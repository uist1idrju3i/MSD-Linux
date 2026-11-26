MSD_DATA_UNLOCK_VERSION = 1
MSD_DATA_UNLOCK_SITE = $(BR2_EXTERNAL_MSD_PATH)/package/msd-data-unlock
MSD_DATA_UNLOCK_SITE_METHOD = local
MSD_DATA_UNLOCK_LICENSE = GPL-2.0-only
MSD_DATA_UNLOCK_LICENSE_FILES = COPYING
MSD_DATA_UNLOCK_DEPENDENCIES = cryptsetup

define MSD_DATA_UNLOCK_BUILD_CMDS
	$(TARGET_CC) $(TARGET_CFLAGS) -Wall -Wextra -Werror -pthread $(TARGET_LDFLAGS) \
		-o $(@D)/msd-data-unlock $(@D)/main.c $(@D)/unlock.c \
		$(@D)/terminal.c $(@D)/crypt-backend.c -lcryptsetup
endef

define MSD_DATA_UNLOCK_INSTALL_TARGET_CMDS
	$(INSTALL) -D -m 0755 $(@D)/msd-data-unlock $(TARGET_DIR)/usr/sbin/msd-data-unlock
endef

$(eval $(generic-package))
