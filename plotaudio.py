import argparse
import queue
import sys

from matplotlib.animation import FuncAnimation
import matplotlib.pyplot as plt
import numpy as np
import sounddevice as sd

INPUT_DEVICE = 1
OUTPUT_DEVICE = 2
SAMPLE_RATE = 48000

def int_or_str(text):
    """Helper function for argument parsing."""
    try:
        return int(text)
    except ValueError:
        return text


parser = argparse.ArgumentParser(add_help=False)
parser.add_argument(
    '-l', '--list-devices', action='store_true',
    help='show list of audio devices and exit')
args, remaining = parser.parse_known_args()
if args.list_devices:
    print(sd.query_devices())
    parser.exit(0)
parser = argparse.ArgumentParser(
    description=__doc__,
    formatter_class=argparse.RawDescriptionHelpFormatter,
    parents=[parser])
parser.add_argument(
    'channels', type=int, default=[1], nargs='*', metavar='CHANNEL',
    help='input channels to plot (default: the first)')
parser.add_argument(
    '-d', '--device', type=int_or_str,
    help='input device (numeric ID or substring)')
parser.add_argument(
    '-w', '--window', type=float, default=500, metavar='DURATION',
    help='visible time slot (default: %(default)s ms)')
parser.add_argument(
    '-i', '--interval', type=float, default=60,
    help='minimum time between plot updates (default: %(default)s ms)')
parser.add_argument(
    '-b', '--blocksize', type=int, help='block size (in samples)')
parser.add_argument(
    '-r', '--samplerate', type=float, default=48000, help='sampling rate of audio device')
parser.add_argument(
    '-n', '--downsample', type=int, default=10, metavar='N',
    help='display every Nth sample (default: %(default)s)')
args = parser.parse_args(remaining)
if any(c < 1 for c in args.channels):
    parser.error('argument CHANNEL: must be >= 1')
mapping = [c - 1 for c in args.channels]  # Channel numbers start with 1
input_q = queue.Queue()
output_q = queue.Queue()

def input_callback(indata, frames, time, status):
    """This is called (from a separate thread) for each audio block."""
    if status:
        print(status, file=sys.stderr)
    # Fancy indexing with mapping creates a (necessary!) copy:
    input_q.put(indata[::args.downsample, mapping])

def output_callback(indata, frames, time, status):
    """This is called (from a separate thread) for each audio block."""
    if status:
        print(status, file=sys.stderr)
    # Fancy indexing with mapping creates a (necessary!) copy:
    output_q.put(indata[::args.downsample, mapping])

def update_plot(frame):
    """This is called by matplotlib for each plot update.

    Typically, audio callbacks happen more frequently than plot updates,
    therefore the queue tends to contain multiple blocks of audio data.

    """
    global input_plotdata
    global output_plotdata

    while True:
        try:
            input_data = input_q.get_nowait()
            output_data = output_q.get_nowait()
        except queue.Empty:
            break
        #Update input data
        input_shift = len(input_data)
        output_shift = len(output_data)
        input_plotdata = np.roll(input_plotdata, -input_shift, axis=0)
        output_plotdata = np.roll(output_plotdata, -output_shift, axis=0)
        input_plotdata[-input_shift:, :] = input_data
        output_plotdata[-output_shift:, :] = output_data
    for column, line in enumerate(lines[0]):
        line.set_ydata(input_plotdata[:, column])
    for column, line in enumerate(lines[1]):
        line.set_ydata(output_plotdata[:, column])
    return lines[0], lines[1],


try:
    if args.samplerate is None:
        print('devices:',args.device)
        device_info = sd.query_devices(args.device, 'input')
        args.samplerate = device_info['default_samplerate']
        print('Samplerate:', args.samplerate)

    length = int(args.window * args.samplerate / (1000 * args.downsample))
    input_plotdata = np.zeros((length, len(args.channels)))
    output_plotdata = np.zeros((length, len(args.channels)))
    print(length)

    fig, ax = plt.subplots(2,1)
    input_line = ax[0].plot(input_plotdata)
    output_line = ax[1].plot(output_plotdata)
    lines = [input_line, output_line]
    if len(args.channels) > 1:
        ax.legend(['channel {}'.format(c) for c in args.channels],
                  loc='lower left', ncol=len(args.channels))
    ax[0].axis((0, len(input_plotdata), -0.7, 0.7))
    ax[1].axis((0, len(output_plotdata), -0.7, 0.7))
    major_ticks = np.arange(0, length, length/args.downsample/5)
    ax[0].set_xticks(major_ticks)
    ax[1].set_xticks(major_ticks)
    ax[0].xaxis.grid(True)
    ax[1].xaxis.grid(True)
    ax[0].tick_params(bottom=False, top=False, labelbottom=False,
                   right=False, left=False, labelleft=False)
    ax[1].tick_params(bottom=False, top=False, labelbottom=False,
                   right=False, left=False, labelleft=False)
    fig.tight_layout(pad=0)

    input_stream = sd.InputStream(
        device=INPUT_DEVICE, channels=2,
        samplerate=SAMPLE_RATE, callback=input_callback)
    output_stream = sd.InputStream(
      device=OUTPUT_DEVICE, channels=2,
      samplerate=SAMPLE_RATE, callback=output_callback)
    ani = FuncAnimation(fig, update_plot, interval=args.interval, blit=False, save_count=500)
    with input_stream, output_stream:
        plt.show()
    # writergif = PillowWriter(fps=args.interval)
    # ani.save('test.gif', writer=writergif)
except Exception as e:
    parser.exit(type(e).__name__ + ': ' + str(e))