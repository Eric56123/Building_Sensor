import spidev

print("SPI Loopback Test...")
spi = spidev.SpiDev()
spi.open(0, 0)
spi.max_speed_hz = 50000

# We send the test byte 0xAA (10101010)
# Because MOSI is wired directly to MISO, we should instantly receive 0xAA back.
response = spi.xfer2([0xAA])

print(f"Sent: 0xAA")
print(f"Received: {hex(response[0]).upper()}")

if response[0] == 0xAA:
    print("\n[PASS] The Raspberry Pi SPI controller and wires are flawless.")
else:
    print("\n[FAIL] The Pi cannot hear itself. Internal damage or broken jumper wire.")

spi.close()