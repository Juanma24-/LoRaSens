/*
 * Copyright (c) 2016, Pycom Limited.
 *
 * This software is licensed under the GNU GPL version 3 or any
 * later version, with permitted additional terms. For more information
 * see the Pycom Licence v1.0 document supplied with this file, or
 * available at https://www.pycom.io/opensource/licensing
 */

#include <string.h>
#include <stdint.h>
#include <stdbool.h>

#include "py/mpconfig.h"
#include "py/obj.h"
#include "bootloader.h"
#include "updater.h"
#include "esp_spi_flash.h"
#include "esp_log.h"
#include "rom/crc.h"


/******************************************************************************
 DEFINE PRIVATE CONSTANTS
 ******************************************************************************/
#define UPDATER_IMG_PATH                                "/flash/sys/appimg.bin"

/******************************************************************************
 DEFINE TYPES
 ******************************************************************************/
typedef struct {
    uint32_t size;
    uint32_t offset;
    uint32_t chunk_size;
    uint32_t current_chunk;
} updater_data_t;

/******************************************************************************
 DECLARE PRIVATE DATA
 ******************************************************************************/
static updater_data_t updater_data = { .size = 0, .offset = 0, .chunk_size = 0, .current_chunk = 0 };
//static OsiLockObj_t updater_LockObj;
static boot_info_t boot_info;
static uint32_t boot_info_offset;

/******************************************************************************
 DEFINE PUBLIC FUNCTIONS
 ******************************************************************************/
void updater_pre_init (void) {
//    // create the updater lock
//    ASSERT(OSI_OK == sl_LockObjCreate(&updater_LockObj, "UpdaterLock"));
}

bool updater_read_boot_info (boot_info_t *boot_info, uint32_t *boot_info_offset) {
    esp_partition_info_t partition_info[PARTITIONS_COUNT];

    // printf("Reading boot info\n");

    if (ESP_OK != spi_flash_read(ESP_PARTITION_TABLE_ADDR, (void *)partition_info, sizeof(partition_info))) {
        return false;
    }
    // get the data from the boot info partition
    if (ESP_OK != spi_flash_read(partition_info[OTA_DATA_INDEX].pos.offset, (void *)boot_info, sizeof(boot_info_t))) {
        return false;
    }
    *boot_info_offset = partition_info[OTA_DATA_INDEX].pos.offset;
    return true;
}

bool updater_check_path (void *path) {
//    sl_LockObjLock (&updater_LockObj, SL_OS_WAIT_FOREVER);
    if (!strcmp(UPDATER_IMG_PATH, path)) {
        return true;
    }
//        sl_LockObjUnlock (&updater_LockObj);
    return false;
}

bool updater_start (void) {
    updater_data.size = IMG_SIZE;
    updater_data.offset = IMG_UPDATE1_OFFSET;

    // check which one should be the next active image
    if (updater_read_boot_info (&boot_info, &boot_info_offset)) {
        // if we still have an image pending for verification, keep overwriting it
        if ((boot_info.Status == IMG_STATUS_CHECK && boot_info.ActiveImg == IMG_ACT_UPDATE2) ||
            (boot_info.ActiveImg == IMG_ACT_UPDATE1 && boot_info.Status != IMG_STATUS_CHECK)) {
            updater_data.offset = IMG_UPDATE2_OFFSET;
        }
    }

    // printf("Updating image at offset=%x\n", updater_data.offset);

    // erase the first 2 sectors
    if (ESP_OK != spi_flash_erase_sector(updater_data.offset / SPI_FLASH_SEC_SIZE)) {
        // printf("Erasing first sector failed!\n");
        return false;
    }
    if (ESP_OK != spi_flash_erase_sector((updater_data.offset + SPI_FLASH_SEC_SIZE) / SPI_FLASH_SEC_SIZE)) {
        // printf("Erasing second sector failed!\n");
        return false;
    }

    boot_info.size = 0;
    updater_data.current_chunk = 0;

    return true;
}

bool updater_write (uint8_t *buf, uint32_t len) {
//    sl_LockObjLock (&wlan_LockObj, SL_OS_WAIT_FOREVER);
    // printf("Writing %d bytes\n", len);
    if (ESP_OK != spi_flash_write(updater_data.offset, (void *)buf, len)) {
        // printf("SPI flash write failed\n");
        return false;
    }

    updater_data.offset += len;
    updater_data.current_chunk += len;
    boot_info.size += len;

    if (updater_data.current_chunk >= SPI_FLASH_SEC_SIZE) {
        updater_data.current_chunk -= SPI_FLASH_SEC_SIZE;
        // erase the next sector
        if (ESP_OK != spi_flash_erase_sector((updater_data.offset + SPI_FLASH_SEC_SIZE) / SPI_FLASH_SEC_SIZE)) {
            // printf("Erasing next sector failed!\n");
            return false;
        }
    }
//    sl_LockObjUnlock (&wlan_LockObj);
    return true;
}

bool updater_finish (void) {
    if (updater_data.offset > 0) {
        // printf("Updater finish\n");
//        sl_LockObjLock (&wlan_LockObj, SL_OS_WAIT_FOREVER);
        // if we still have an image pending for verification, leave the boot info as it is
        if (boot_info.Status != IMG_STATUS_CHECK) {
            // printf("Saving new boot info\n");
            // save the new boot info
            boot_info.PrevImg = boot_info.ActiveImg;
            if (boot_info.ActiveImg == IMG_ACT_UPDATE1) {
                boot_info.ActiveImg = IMG_ACT_UPDATE2;
            } else {
                boot_info.ActiveImg = IMG_ACT_UPDATE1;
            }

            boot_info.Status = IMG_STATUS_CHECK;
            boot_info.crc = crc32_le(UINT32_MAX, (uint8_t*)&boot_info.ActiveImg,
                                                 sizeof(boot_info) - sizeof(boot_info.crc));

            if (ESP_OK != spi_flash_erase_sector(boot_info_offset / SPI_FLASH_SEC_SIZE)) {
                // printf("Erasing boot info failed\n");
                return false;
            }

            if (ESP_OK != spi_flash_write(boot_info_offset, (void *)&boot_info, sizeof(boot_info_t))) {
                // printf("Saving boot info failed\n");
                return false;
            }
            // printf("Boot info saved OK\n");
        }
//        sl_LockObjUnlock (&wlan_LockObj);
        updater_data.offset = 0;
    }
//    sl_LockObjUnlock (&updater_LockObj);
    return true;
}

