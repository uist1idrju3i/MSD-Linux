M5STACK_CARDPUTERZERO_VERSION = 75518549a2640486f5d13ea72ca4935b198d7c20
M5STACK_CARDPUTERZERO_SITE = $(BR2_EXTERNAL_MSD_PATH)/vendor/m5stack-linux-dtoverlays
M5STACK_CARDPUTERZERO_SITE_METHOD = local
M5STACK_CARDPUTERZERO_LICENSE = GPL-2.0
M5STACK_CARDPUTERZERO_LICENSE_FILES = COPYING
M5STACK_CARDPUTERZERO_DEPENDENCIES += host-dtc
M5STACK_CARDPUTERZERO_MODULE_SUBDIRS = \
	modules/CardputerZero \
	modules/st7789v-1.0 \
	modules/m5ioe1-1.0 \
	modules/tca8418-1.0 \
	modules/es8389-1.0 \
	modules/bq27220-1.0 \
	modules/imu-1.0/bmi270 \
	modules/imu-1.0/magnetometer
M5STACK_CARDPUTERZERO_MODULE_MAKE_OPTS = \
	CONFIG_BMC150_MAGN=m \
	CONFIG_BMC150_MAGN_BMI270=m \
	CONFIG_BMI270=m \
	CONFIG_BMI270_I2C=m \
	KCFLAGS=-DCONFIG_CARDPUTERO_V0_5=1

$(eval $(kernel-module))

define M5STACK_CARDPUTERZERO_BUILD_OVERLAYS
	mkdir -p $(BINARIES_DIR)/overlays
	set -e; \
	for overlay in \
		modules/CardputerZero/cardputerzero-v5-overlay.dts \
		modules/bq27220-1.0/bq27220_v5.dts \
		modules/imu-1.0/bmi270_bmm150_overlay.dts; do \
		base=$${overlay##*/}; \
		base=$${base%.dts}; \
		$(HOSTCC) -E -nostdinc -undef -x assembler-with-cpp \
			-DCONFIG_CARDPUTERO_V0_5=1 "$(@D)/$$overlay" \
			-o "$(@D)/$$base.dts.tmp"; \
		$(HOST_DIR)/bin/dtc -@ -I dts -O dtb \
			-o "$(BINARIES_DIR)/overlays/$$base.dtbo" \
			"$(@D)/$$base.dts.tmp"; \
		rm -f "$(@D)/$$base.dts.tmp"; \
	done
endef
M5STACK_CARDPUTERZERO_POST_BUILD_HOOKS += M5STACK_CARDPUTERZERO_BUILD_OVERLAYS

define M5STACK_CARDPUTERZERO_INSTALL_TARGET_CMDS
	$(INSTALL) -D -m 0644 \
		$(@D)/modules/st7789v-1.0/cardputerzero,st7789v_lcd.bin \
		$(TARGET_DIR)/lib/firmware/cardputerzero,st7789v_lcd.bin
	$(INSTALL) -D -m 0644 \
		$(@D)/modules/imu-1.0/bmi270-init-data.fw \
		$(TARGET_DIR)/lib/firmware/bmi270-init-data.fw
	$(INSTALL) -D -m 0644 \
		$(@D)/modules/tca8418-1.0/tca8418_keypad_m5stack_keymap.map \
		$(TARGET_DIR)/usr/share/keymaps/tca8418_keypad_m5stack_keymap.map
endef

$(eval $(generic-package))
