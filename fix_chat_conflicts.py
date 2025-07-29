#!/usr/bin/env python3
"""
Script to analyze and fix chat-related conflicts in the DICOM viewer application.
This script will:
1. Check for database consistency issues
2. Verify model relationships
3. Fix any orphaned chat messages
4. Ensure proper user-facility relationships
5. Validate chat message types
"""

import os
import sys
import django
from datetime import datetime

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'noctisview.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    django.setup()
except Exception as e:
    print(f"Error setting up Django: {e}")
    print("Please ensure Django is installed and DJANGO_SETTINGS_MODULE is set correctly")
    sys.exit(1)

from django.db import connection, transaction
from django.contrib.auth.models import User
from viewer.models import ChatMessage, Facility, DicomStudy, Notification

class ChatConflictResolver:
    def __init__(self):
        self.conflicts = []
        self.fixes_applied = []
        
    def analyze_conflicts(self):
        """Analyze all potential chat-related conflicts"""
        print("Starting chat conflict analysis...")
        print("=" * 60)
        
        # Check 1: Orphaned messages (no sender)
        self.check_orphaned_messages()
        
        # Check 2: Invalid message types
        self.check_invalid_message_types()
        
        # Check 3: Messages with both recipient and facility
        self.check_recipient_facility_conflicts()
        
        # Check 4: Messages without proper relationships
        self.check_missing_relationships()
        
        # Check 5: Duplicate messages
        self.check_duplicate_messages()
        
        # Check 6: Database integrity
        self.check_database_integrity()
        
        return self.conflicts
    
    def check_orphaned_messages(self):
        """Check for messages without valid senders"""
        print("\n1. Checking for orphaned messages...")
        
        try:
            # Find messages where sender doesn't exist
            orphaned = ChatMessage.objects.filter(sender__isnull=True)
            if orphaned.exists():
                count = orphaned.count()
                self.conflicts.append({
                    'type': 'orphaned_messages',
                    'count': count,
                    'description': f'Found {count} messages without valid senders',
                    'severity': 'high'
                })
                print(f"   ❌ Found {count} orphaned messages")
            else:
                print("   ✅ No orphaned messages found")
                
        except Exception as e:
            print(f"   ⚠️  Error checking orphaned messages: {e}")
            
    def check_invalid_message_types(self):
        """Check for messages with invalid types"""
        print("\n2. Checking for invalid message types...")
        
        valid_types = [choice[0] for choice in ChatMessage.MESSAGE_TYPES]
        invalid = ChatMessage.objects.exclude(message_type__in=valid_types)
        
        if invalid.exists():
            count = invalid.count()
            self.conflicts.append({
                'type': 'invalid_message_types',
                'count': count,
                'description': f'Found {count} messages with invalid types',
                'severity': 'medium'
            })
            print(f"   ❌ Found {count} messages with invalid types")
        else:
            print("   ✅ All message types are valid")
            
    def check_recipient_facility_conflicts(self):
        """Check for messages with both recipient and facility set"""
        print("\n3. Checking for recipient/facility conflicts...")
        
        conflicted = ChatMessage.objects.filter(
            recipient__isnull=False,
            facility__isnull=False
        )
        
        if conflicted.exists():
            count = conflicted.count()
            self.conflicts.append({
                'type': 'recipient_facility_conflict',
                'count': count,
                'description': f'Found {count} messages with both recipient and facility',
                'severity': 'low'
            })
            print(f"   ⚠️  Found {count} messages with both recipient and facility")
        else:
            print("   ✅ No recipient/facility conflicts found")
            
    def check_missing_relationships(self):
        """Check for messages without proper relationships"""
        print("\n4. Checking for missing relationships...")
        
        # Messages without recipient or facility
        no_target = ChatMessage.objects.filter(
            recipient__isnull=True,
            facility__isnull=True
        )
        
        if no_target.exists():
            count = no_target.count()
            self.conflicts.append({
                'type': 'missing_target',
                'count': count,
                'description': f'Found {count} messages without recipient or facility',
                'severity': 'high'
            })
            print(f"   ❌ Found {count} messages without target")
        else:
            print("   ✅ All messages have proper targets")
            
    def check_duplicate_messages(self):
        """Check for duplicate messages"""
        print("\n5. Checking for duplicate messages...")
        
        # Find messages with same sender, recipient, message, and timestamp
        from django.db.models import Count
        
        duplicates = ChatMessage.objects.values(
            'sender', 'recipient', 'message', 'created_at'
        ).annotate(
            count=Count('id')
        ).filter(count__gt=1)
        
        if duplicates:
            total_duplicates = sum(d['count'] - 1 for d in duplicates)
            self.conflicts.append({
                'type': 'duplicate_messages',
                'count': total_duplicates,
                'description': f'Found {total_duplicates} duplicate messages',
                'severity': 'medium'
            })
            print(f"   ⚠️  Found {total_duplicates} duplicate messages")
        else:
            print("   ✅ No duplicate messages found")
            
    def check_database_integrity(self):
        """Check database integrity for chat-related tables"""
        print("\n6. Checking database integrity...")
        
        try:
            with connection.cursor() as cursor:
                # Check foreign key constraints
                cursor.execute("""
                    SELECT COUNT(*) FROM viewer_chatmessage 
                    WHERE sender_id NOT IN (SELECT id FROM auth_user)
                """)
                invalid_senders = cursor.fetchone()[0]
                
                if invalid_senders > 0:
                    self.conflicts.append({
                        'type': 'invalid_foreign_keys',
                        'count': invalid_senders,
                        'description': f'Found {invalid_senders} messages with invalid sender IDs',
                        'severity': 'critical'
                    })
                    print(f"   ❌ Found {invalid_senders} messages with invalid sender IDs")
                else:
                    print("   ✅ All foreign key constraints are valid")
                    
        except Exception as e:
            print(f"   ⚠️  Error checking database integrity: {e}")
            
    def fix_conflicts(self, auto_fix=False):
        """Fix identified conflicts"""
        if not self.conflicts:
            print("\n✅ No conflicts found to fix!")
            return
            
        print("\n" + "=" * 60)
        print("CONFLICT RESOLUTION")
        print("=" * 60)
        
        for conflict in self.conflicts:
            print(f"\nConflict: {conflict['description']}")
            print(f"Severity: {conflict['severity']}")
            
            if not auto_fix and conflict['severity'] in ['high', 'critical']:
                response = input("Fix this conflict? (y/n): ")
                if response.lower() != 'y':
                    continue
                    
            # Apply fixes based on conflict type
            if conflict['type'] == 'orphaned_messages':
                self.fix_orphaned_messages()
            elif conflict['type'] == 'invalid_message_types':
                self.fix_invalid_message_types()
            elif conflict['type'] == 'missing_target':
                self.fix_missing_targets()
            elif conflict['type'] == 'duplicate_messages':
                self.fix_duplicate_messages()
            elif conflict['type'] == 'invalid_foreign_keys':
                self.fix_invalid_foreign_keys()
                
    def fix_orphaned_messages(self):
        """Fix orphaned messages by deleting them"""
        print("   Fixing orphaned messages...")
        try:
            with transaction.atomic():
                count = ChatMessage.objects.filter(sender__isnull=True).delete()[0]
                self.fixes_applied.append(f"Deleted {count} orphaned messages")
                print(f"   ✅ Deleted {count} orphaned messages")
        except Exception as e:
            print(f"   ❌ Error fixing orphaned messages: {e}")
            
    def fix_invalid_message_types(self):
        """Fix invalid message types by setting to default"""
        print("   Fixing invalid message types...")
        try:
            with transaction.atomic():
                valid_types = [choice[0] for choice in ChatMessage.MESSAGE_TYPES]
                invalid = ChatMessage.objects.exclude(message_type__in=valid_types)
                count = invalid.update(message_type='user_chat')
                self.fixes_applied.append(f"Fixed {count} invalid message types")
                print(f"   ✅ Fixed {count} invalid message types")
        except Exception as e:
            print(f"   ❌ Error fixing message types: {e}")
            
    def fix_missing_targets(self):
        """Fix messages without targets by setting a default facility"""
        print("   Fixing missing targets...")
        try:
            with transaction.atomic():
                # Get or create a default facility
                default_facility, created = Facility.objects.get_or_create(
                    name="System",
                    defaults={'address': 'System Generated', 'contact': 'N/A'}
                )
                
                no_target = ChatMessage.objects.filter(
                    recipient__isnull=True,
                    facility__isnull=True
                )
                count = no_target.update(facility=default_facility)
                self.fixes_applied.append(f"Fixed {count} messages without targets")
                print(f"   ✅ Fixed {count} messages without targets")
        except Exception as e:
            print(f"   ❌ Error fixing missing targets: {e}")
            
    def fix_duplicate_messages(self):
        """Remove duplicate messages, keeping the oldest"""
        print("   Fixing duplicate messages...")
        try:
            with transaction.atomic():
                from django.db.models import Count, Min
                
                # Find groups of duplicates
                duplicates = ChatMessage.objects.values(
                    'sender', 'recipient', 'message', 'created_at'
                ).annotate(
                    count=Count('id'),
                    min_id=Min('id')
                ).filter(count__gt=1)
                
                total_deleted = 0
                for dup in duplicates:
                    # Delete all but the first occurrence
                    to_delete = ChatMessage.objects.filter(
                        sender=dup['sender'],
                        recipient=dup['recipient'],
                        message=dup['message'],
                        created_at=dup['created_at']
                    ).exclude(id=dup['min_id'])
                    
                    deleted = to_delete.delete()[0]
                    total_deleted += deleted
                    
                self.fixes_applied.append(f"Deleted {total_deleted} duplicate messages")
                print(f"   ✅ Deleted {total_deleted} duplicate messages")
        except Exception as e:
            print(f"   ❌ Error fixing duplicates: {e}")
            
    def fix_invalid_foreign_keys(self):
        """Fix invalid foreign key references"""
        print("   Fixing invalid foreign keys...")
        try:
            with connection.cursor() as cursor:
                # Delete messages with invalid sender IDs
                cursor.execute("""
                    DELETE FROM viewer_chatmessage 
                    WHERE sender_id NOT IN (SELECT id FROM auth_user)
                """)
                deleted = cursor.rowcount
                self.fixes_applied.append(f"Deleted {deleted} messages with invalid sender IDs")
                print(f"   ✅ Deleted {deleted} messages with invalid sender IDs")
        except Exception as e:
            print(f"   ❌ Error fixing foreign keys: {e}")
            
    def generate_report(self):
        """Generate a summary report"""
        print("\n" + "=" * 60)
        print("CHAT CONFLICT ANALYSIS REPORT")
        print("=" * 60)
        print(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Total Messages: {ChatMessage.objects.count()}")
        print(f"Total Users: {User.objects.count()}")
        print(f"Total Facilities: {Facility.objects.count()}")
        
        if self.conflicts:
            print(f"\nConflicts Found: {len(self.conflicts)}")
            for conflict in self.conflicts:
                print(f"  - {conflict['description']} (Severity: {conflict['severity']})")
        else:
            print("\n✅ No conflicts found!")
            
        if self.fixes_applied:
            print(f"\nFixes Applied: {len(self.fixes_applied)}")
            for fix in self.fixes_applied:
                print(f"  - {fix}")
                
        # Message statistics
        print("\nMessage Statistics:")
        print(f"  - System Upload Messages: {ChatMessage.objects.filter(message_type='system_upload').count()}")
        print(f"  - User Chat Messages: {ChatMessage.objects.filter(message_type='user_chat').count()}")
        print(f"  - Unread Messages: {ChatMessage.objects.filter(is_read=False).count()}")
        
        # Check for any remaining issues
        print("\nFinal Status:")
        remaining_issues = ChatMessage.objects.filter(
            sender__isnull=True
        ).count() + ChatMessage.objects.filter(
            recipient__isnull=True,
            facility__isnull=True
        ).count()
        
        if remaining_issues == 0:
            print("✅ All chat conflicts have been resolved!")
        else:
            print(f"⚠️  {remaining_issues} issues remain")

def main():
    """Main function to run the conflict resolver"""
    resolver = ChatConflictResolver()
    
    print("DICOM Viewer Chat Conflict Analyzer")
    print("===================================\n")
    
    # Analyze conflicts
    conflicts = resolver.analyze_conflicts()
    
    if conflicts:
        print(f"\n⚠️  Found {len(conflicts)} conflict types")
        
        # Ask user if they want to fix
        response = input("\nWould you like to fix these conflicts? (y/n/auto): ")
        if response.lower() == 'y':
            resolver.fix_conflicts(auto_fix=False)
        elif response.lower() == 'auto':
            resolver.fix_conflicts(auto_fix=True)
    
    # Generate final report
    resolver.generate_report()

if __name__ == "__main__":
    main()