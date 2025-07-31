#!/bin/bash

# Fix VirtualBox VMX Root Mode Issue
# This script addresses the VERR_VMX_IN_VMX_ROOT_MODE error

echo "=== VirtualBox VMX Root Mode Issue Fix ==="
echo

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo "Please run this script as a regular user (it will use sudo when needed)"
   exit 1
fi

echo "1. Checking current virtualization status..."
if grep -q "hypervisor" /proc/cpuinfo; then
    echo "   ✓ Running in a virtualized environment"
    NESTED_VIRT=true
else
    echo "   • Running on physical hardware"
    NESTED_VIRT=false
fi

# Check for hardware virtualization support
if grep -q -E "(vmx|svm)" /proc/cpuinfo; then
    echo "   ✓ Hardware virtualization support detected"
else
    echo "   ! No hardware virtualization support available"
    echo "   → VirtualBox will need to use software virtualization"
fi

echo
echo "2. Configuring KVM module blacklist..."

# Create KVM blacklist configuration
sudo tee /etc/modprobe.d/blacklist-kvm.conf > /dev/null << 'KVMEOF'
# Blacklist KVM modules to prevent conflicts with VirtualBox
blacklist kvm
blacklist kvm_intel
blacklist kvm_amd
blacklist kvm_x86
KVMEOF

# Create additional KVM disable configuration
sudo tee /etc/modprobe.d/disable-kvm.conf > /dev/null << 'KVMEOF2'
# Additional KVM disabling options
options kvm ignore_msrs=1
options kvm halt_poll_ns=0
install kvm /bin/true
install kvm_intel /bin/true
install kvm_amd /bin/true
KVMEOF2

echo "   ✓ Created KVM blacklist configurations"

echo
echo "3. Unloading KVM modules if currently loaded..."

# Try to unload KVM modules
for module in kvm_intel kvm_amd kvm; do
    if lsmod | grep -q "^$module" 2>/dev/null; then
        echo "   • Unloading $module..."
        sudo rmmod "$module" 2>/dev/null || echo "   ! Could not unload $module (may be built-in)"
    fi
done

echo
echo "4. Configuring VirtualBox for software virtualization..."

# Check if VirtualBox is installed
if ! command -v VBoxManage &> /dev/null; then
    echo "   ! VirtualBox not found. Installing..."
    sudo apt update && sudo apt install -y virtualbox
fi

# Add user to vboxusers group
sudo usermod -a -G vboxusers $USER

# Create VirtualBox configuration directory
mkdir -p ~/.config/VirtualBox

# Create a configuration that disables hardware virtualization
cat > ~/.config/VirtualBox/VirtualBox.xml << 'VBOXEOF'
<?xml version="1.0" encoding="UTF-8"?>
<VirtualBox xmlns="http://www.virtualbox.org/" version="1.12-linux">
  <Global>
    <ExtraData>
      <ExtraDataItem name="GUI/SuppressMessages" value="remindAboutWrongColorDepth,remindAboutAutoCapture,remindAboutMouseIntegrationOff,remindAboutMouseIntegrationOn,remindAboutPausedVMInput"/>
      <ExtraDataItem name="VBoxInternal/HWVIRTEX" value="0"/>
      <ExtraDataItem name="VBoxInternal/EnableNestedPaging" value="0"/>
    </ExtraData>
  </Global>
</VirtualBox>
VBOXEOF

echo "   ✓ Configured VirtualBox for software virtualization"

echo
echo "5. Creating VirtualBox startup configuration..."

# Create a script to ensure VirtualBox uses software virtualization
sudo tee /usr/local/bin/virtualbox-software-mode << 'STARTEOF'
#!/bin/bash
# Force VirtualBox to use software virtualization
export VBOX_VER_INFO_DEV=1
export VBOX_LOG=
export VBOX_LOG_FLAGS=

# Disable hardware acceleration
export VBoxInternal_HWVIRTEX=0
export VBoxInternal_EnableNestedPaging=0

# Launch VirtualBox
exec /usr/bin/virtualbox "$@"
STARTEOF

sudo chmod +x /usr/local/bin/virtualbox-software-mode

echo "   ✓ Created VirtualBox software mode launcher"

echo
echo "6. Generating kernel parameter recommendations..."

if [ -f /etc/default/grub ]; then
    echo "   • To completely disable KVM at boot, add these parameters to GRUB_CMDLINE_LINUX:"
    echo "     kvm.ignore_msrs=1 kvm.halt_poll_ns=0"
    echo "   • Edit /etc/default/grub and run 'sudo update-grub' after adding the parameters"
elif [ -d /boot/loader/entries ]; then
    echo "   • For systemd-boot, add these parameters to your boot entries:"
    echo "     kvm.ignore_msrs=1 kvm.halt_poll_ns=0"
else
    echo "   • Add these kernel parameters to your bootloader configuration:"
    echo "     kvm.ignore_msrs=1 kvm.halt_poll_ns=0"
fi

echo
echo "7. Final steps and recommendations..."

echo "   ✓ KVM modules blacklisted"
echo "   ✓ VirtualBox configured for software virtualization"
echo "   ✓ Created software mode launcher"

echo
echo "NEXT STEPS:"
echo "1. Reboot your system to ensure all changes take effect"
echo "2. After reboot, use 'virtualbox-software-mode' to launch VirtualBox"
echo "3. Or modify existing VMs to disable hardware virtualization in VM settings:"
echo "   - VM Settings → System → Acceleration → Uncheck 'Enable VT-x/AMD-V'"
echo "   - VM Settings → System → Acceleration → Uncheck 'Enable Nested Paging'"

if [ "$NESTED_VIRT" = true ]; then
    echo
    echo "NESTED VIRTUALIZATION NOTES:"
    echo "• You're running in a VM, so performance will be limited"
    echo "• Consider using container technologies (Docker, LXC) instead"
    echo "• Or use the host machine's VirtualBox installation directly"
fi

echo
echo "VERIFICATION:"
echo "After reboot, run: lsmod | grep kvm"
echo "Result should be empty (no KVM modules loaded)"

echo
echo "=== Fix script completed ==="
