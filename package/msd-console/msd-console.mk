MSD_CONSOLE_VERSION = 1
MSD_CONSOLE_SITE = $(BR2_EXTERNAL_MSD_PATH)/package/msd-console
MSD_CONSOLE_SITE_METHOD = local
MSD_CONSOLE_LICENSE = GPL-2.0-only
MSD_CONSOLE_LICENSE_FILES = COPYING

define MSD_CONSOLE_BUILD_CMDS
	$(TARGET_CC) $(TARGET_CFLAGS) $(TARGET_LDFLAGS) -o $(@D)/msd-console $(@D)/msd-console.c
endef

define MSD_CONSOLE_INSTALL_TARGET_CMDS
	$(INSTALL) -D -m 0755 $(@D)/msd-console $(TARGET_DIR)/usr/bin/msd-console
endef

$(eval $(generic-package))
