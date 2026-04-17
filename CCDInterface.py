import serial
import matplotlib.pyplot as plt
import numpy as np
import time

# ==========================================
# CONFIGURATION
# ==========================================
SERIAL_PORT = '/dev/ttyACM0' 
BAUD_RATE = 115200
TOTAL_PIXELS = 4000          # STM32 tarafındaki CCD_PIXEL_COUNT ile aynı olmalı
EXPECTED_BYTES = TOTAL_PIXELS * 2  # Her pixel 2 byte (uint16)
IGNORE_LAST = 306            # 4000 - 3694 = 306 dummy/idle pixels
PLOT_COUNT = TOTAL_PIXELS - IGNORE_LAST
MAX_ADC_VAL = 4096
GAIN = 1 

def read_full_frame(ser, size):
    """Verilen boyutta veriyi parça parça birleştirerek okur."""
    data = b''
    while len(data) < size:
        chunk = ser.read(size - len(data))
        if not chunk:
            return None  # Timeout oluştu
        data += chunk
    return data

def main():
    try:
        # Timeout değerini 2 saniye yapalım (Entegrasyon süresi uzun olabilir)
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=2)
        ser.reset_input_buffer()
        print(f"Connected to {SERIAL_PORT}...")
    except Exception as e:
        print(f"Error: {e}")
        return

    # Initialize Plot
    plt.ion()
    fig, ax = plt.subplots(figsize=(12, 6))
    x_data = np.arange(PLOT_COUNT)
    line, = ax.plot(x_data, np.zeros(PLOT_COUNT), 'r-', linewidth=0.8)
    
    ax.set_ylim(0, MAX_ADC_VAL * GAIN)
    ax.set_xlim(0, PLOT_COUNT)
    ax.set_title("TCD1304 Real-Time Readout")
    ax.set_xlabel("Pixel Index")
    ax.set_ylabel("Intensity")
    ax.grid(True, alpha=0.3)

    try:
        while True:
            # 1. 'S' (Start Byte) bekle
            char = ser.read(1)
            if char == b'S':
                # 2. Tam olarak 8000 byte oku (Parça parça gelse bile bekler)
                raw_data = read_full_frame(ser, EXPECTED_BYTES)
                #print(len(raw_data))
                if raw_data is None:
                    print("Timeout: Frame eksik geldi.")
                    continue

                # 3. 'F' (Stop Byte) kontrol et
                footer = ser.read(1)

                if footer == b'F':
                    # Veriyi uint16 (Little Endian) formatına çevir
                    pixel_data = np.frombuffer(raw_data, dtype='<u2')
                    
                    # TCD1304 genelde ters çalışır (Işık arttıkça ADC değeri düşer)
                    # Bu yüzden MAX_ADC_VAL'den çıkarıyoruz
                    plot_data = ((MAX_ADC_VAL - pixel_data).astype(np.float32) * GAIN)[:PLOT_COUNT]
                    
                    # Grafiği güncelle
                    line.set_ydata(plot_data)
                    fig.canvas.draw()
                    fig.canvas.flush_events()
                else:
                    print("Hata: Footer ('F') bulunamadı, senkronizasyon kaydı.")
                    ser.reset_input_buffer() # Buffer'ı temizle ki bir sonraki 'S'yi bulabilsin
            
    except KeyboardInterrupt:
        print("Closing...")
    finally:
        ser.close()

if __name__ == "__main__":
    main()
