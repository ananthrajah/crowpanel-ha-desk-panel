#pragma once
// usb_disable.h — v1.0.0 (unchanged since 2026-10-15). Used by crowpanel-desk.yaml.
// Workaround for ESPHome >= 2026.3 "I2C software timeout" on GPIO19/20 (shared with
// the ESP32-S3 USB-Serial-JTAG PHY). Without it the GT911 touch on CrowPanel 7" V3.0
// stops responding. Source: esphome/esphome#15356 and devices.esphome.io PR #1494.
// Flashing still works: the CrowPanel's USB-C goes through a USB-UART bridge, not JTAG.

#include "soc/usb_serial_jtag_reg.h"
#include "soc/io_mux_reg.h"
#include "hal/usb_serial_jtag_ll.h"

static __attribute__((constructor(101))) void disable_usb_serial_jtag_phy() {
  usb_serial_jtag_ll_phy_enable_pad(false);
  CLEAR_PERI_REG_MASK(USB_SERIAL_JTAG_CONF0_REG, USB_SERIAL_JTAG_USB_PAD_ENABLE);
  CLEAR_PERI_REG_MASK(USB_SERIAL_JTAG_CONF0_REG, USB_SERIAL_JTAG_DP_PULLUP);
  PIN_FUNC_SELECT(IO_MUX_GPIO19_REG, PIN_FUNC_GPIO);
  PIN_FUNC_SELECT(IO_MUX_GPIO20_REG, PIN_FUNC_GPIO);
  PIN_INPUT_ENABLE(IO_MUX_GPIO19_REG);
  PIN_INPUT_ENABLE(IO_MUX_GPIO20_REG);
  REG_SET_BIT(IO_MUX_GPIO19_REG, FUN_PU);
  REG_SET_BIT(IO_MUX_GPIO20_REG, FUN_PU);
  REG_CLR_BIT(IO_MUX_GPIO19_REG, FUN_PD);
  REG_CLR_BIT(IO_MUX_GPIO20_REG, FUN_PD);
}
