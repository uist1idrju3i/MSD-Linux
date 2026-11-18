MSD_SYNCFS_VERSION = 1
MSD_SYNCFS_SITE = $(BR2_EXTERNAL_MSD_PATH)/package/msd-syncfs
MSD_SYNCFS_SITE_METHOD = local
MSD_SYNCFS_LICENSE = GPL-2.0-only
MSD_SYNCFS_LICENSE_FILES = COPYING

define MSD_SYNCFS_BUILD_CMDS
	$(TARGET_CC) $(TARGET_CFLAGS) $(TARGET_LDFLAGS) -o $(@D)/msd-syncfs $(@D)/msd-syncfs.c
endef

define MSD_SYNCFS_INSTALL_TARGET_CMDS
	$(INSTALL) -D -m 0755 $(@D)/msd-syncfs $(TARGET_DIR)/usr/sbin/msd-syncfs
endef

$(eval $(generic-package))
