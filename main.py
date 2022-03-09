import sounddevice as sd
import soundfile as sf
from scipy.io.wavfile import write
from matplotlib.animation import FuncAnimation
import matplotlib.pyplot as plt
import numpy as np

fs = 48000  # Sample rate
seconds = 3  # Duration of recording
duration = 2
# print(sd.default.device[0])
sd.default.device = [2,5]

def record():
    myrecording = sd.rec(int(seconds * fs), samplerate=fs, channels=2)
    print('Recording')
    sd.wait()  # Wait until recording is finished
    print('Finished')
    write('output.wav', fs, myrecording)  # Save as WAV file

def play():
    filename = 'output.wav'
    # Extract data and sampling rate from file
    data, fs = sf.read(filename, dtype='float32')
    print(data)
    print(fs)
    sd.play(data, fs)
    status = sd.wait()  # Wait until file is done playing

firsttime = None
lasttime = None
def measure_latency():
    # data = []
    def callback(indata, outdata, frames, time, status):
        global firsttime
        global lasttime
        if status:
            print(status)
        # data.append(indata)
        # print(time.currentTime, time.inputBufferAdcTime, len(indata))
        if firsttime is None:
            firsttime = time.currentTime
        # outdata[:] = indata
        if lasttime is not None:
            print(lasttime-time.currentTime)
        lasttime = time.currentTime

    with sd.Stream(channels=1, callback=callback):
        print('recording')
        sd.sleep(int(duration * 1000))
    print(lasttime-firsttime)
    # data = np.array(data)
    # plt.plot(data[:,0], data[:,1])
    # plt.show()

if __name__ == '__main__':
    # measure_latency()
    # play()
    record()