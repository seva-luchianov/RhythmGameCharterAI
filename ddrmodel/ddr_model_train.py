#BAAM
import os
import re

import tensorflow as tf
from tensorflow import keras
from tensorflow.keras.callbacks import LambdaCallback
#from tensorflow.keras.models import Sequential
from tensorflow.keras import layers
from tensorflow.keras import models
from tensorflow.keras.layers import *
from tensorflow.keras.optimizers import RMSprop
from tensorflow.keras.models import load_model
from keras.utils import to_categorical
import numpy as np
import random
import sys
import io
#Note: Requires both ddr_finder and ddr_to_generic to be run first
#will dynamically construct both the MND's data and the output to compare against
#Current input is purely the previous arrows' positions/type (basic arrow, freeze start, freeze end, none)x4
#none is used only for start of song data
#Later revision will use the actual song data as well, but that is not included in this prototype
source_dir = "../preprocessing/ddr_data"
def song_data(skipto = ""):
    for (dirpath, dirnames, filenames) in os.walk(source_dir):
        if skipto != "":
            if skipto in dirpath:
                skipto = ""
            else:
                continue
        name = os.path.relpath(dirpath, source_dir)
        if len(dirnames) > 5:
            print(">Subdirectories found in "+name+", continuing.")
            continue
        if dirnames:
            print("----<5 subdirectories in "+name+", investigate!")
        if not "chart_data.dat" in filenames:
            print("Chart data not found! "+name)
            continue
        with open(os.path.join(dirpath, "chart_data.dat"), encoding="utf-8") as chart_data:
            (a, chart_path) = chart_data.readline().strip().split("=")
            (b, music_path) = chart_data.readline().strip().split("=")
            (c, bpm)        = chart_data.readline().strip().split("=")
            (d, offset)     = chart_data.readline().strip().split("=")
            assert (a, b, c, d) == ("CHART", "MUSIC", "BPM", "OFFSET")
            with open(chart_path, encoding="latin-1") as chart:
                while True:
                    tmp = chart_data.readline()
                    if len(tmp) < 3:
                        break
                    (difficulty, position) = tmp.strip().split("@")
                    difficulty = difficulty.strip(":")
                    chart.seek(int(position))
                    this_difficulty_file = os.path.join(dirpath,"c"+str(difficulty)+"_"+position+".mnd")
                    if os.path.exists(this_difficulty_file):
                        yield (this_difficulty_file,float(bpm),mnd_data(chart))


def mnd_data(chart):
    #Assumes chart is valid and was seek()'d to already
    time_point = 0
    stored_lines = []
    mnd_data = []
    output = []
    last_time = 0
    while True:
        line = chart.readline()
        if len(line) == 0:
            raise Exception("Unexpected EoF!")
        line = line.strip()
        if ";" in line or "," in line:
            #process a measure
            count = len(stored_lines)
            if not count in [4, 8, 12, 16, 24, 32, 48, 64, 96, 192]:
                raise Exception(f"bad count({count}) at {chart.tell()}")
            time_resolution = 192//count #integer division
            for notes in stored_lines:
                note = notes.count("1")
                #Does nothing with mines, maybe make them notes? ("M")
                start_long = notes.count("2")+notes.count("4")
                #Counting rolls (4) as long notes
                end_long = notes.count("3")
                if (note or start_long or end_long):
                    notes = notes.replace("M","0").replace("4","2")
                    tmp = list(map(lambda x: to_categorical(x, num_classes=4,dtype="int32"),notes))
                    output.append(tmp)
                    mnd_data.append((time_point, note, start_long, end_long))
                    last_time = time_point
                time_point += time_resolution
            stored_lines = []
        else:
            if len(line) == 4:
                stored_lines.append(line)
        if ";" in line:
            return (mnd_data, output)

LSTM_HISTORY_LENGTH = 64

mnd_input = layers.Input(shape=(7,),name="mnd_input")
x = layers.Dense(32)(mnd_input)
x = layers.Dense(32)(x)
hist_input = layers.Input(shape=(LSTM_HISTORY_LENGTH,4,),name="hist_input")
hist_lstm = layers.LSTM(32)(hist_input)
x = layers.concatenate([x,hist_lstm])
x = layers.Dense(32)(x)
x = layers.Dense(32)(x)
x = layers.Dense(32)(x)
outL = layers.Dense(4, activation='softmax', name = "outL")(x)
outU = layers.Dense(4, activation='softmax', name = "outU")(x)
outD = layers.Dense(4, activation='softmax', name = "outD")(x)
outR = layers.Dense(4, activation='softmax', name = "outR")(x)

#optimizer = RMSprop(learning_rate=0.001)
optimizer = keras.optimizers.Nadam()
model = models.Model(inputs=[mnd_input,hist_input],outputs=[outL,outU,outD,outR])

model.compile(loss='categorical_crossentropy', optimizer=optimizer)

skipname = ""
if len(sys.argv) > 1:
    if sys.argv[1] == "LOAD":
        model = load_model("ddr_model.h5")
    if len(sys.argv) > 2:
        skipname = sys.argv[2]

def beat_find(time_point):
    for tt in [48, 24, 16, 12, 8, 6, 4, 3, 2, 1]: #time_resolution of individual notes
        if time_point%tt == 0:
            return tt
    raise Exception(f"beat_frac {time_point} not int")
    
def generate_song_inout_data(mnd_arr, out_arr, bpm):
    assert(len(mnd_arr) == len(out_arr))
    inputs = []
    outputs = []
    maxouts = []
    fulldata = []
    for i in range(LSTM_HISTORY_LENGTH):
        inputs.append(np.array([0, 0, 0, 0, 0, 0, bpm]))
        maxouts.append([0, 0, 0, 0])
        outputs.append(to_categorical([0, 0, 0, 0],4))
    last_time = 0
    for pos in range(len(mnd_arr)):
        i = pos+LSTM_HISTORY_LENGTH
        (time_point, note, start_long, end_long) = mnd_arr[pos]
        beat_fract = beat_find(time_point)
        next_time = mnd_arr[pos+1][0] if i+1 < len(mnd_arr) else time_point+1920
        mnd_data = np.array([time_point-last_time, next_time-time_point, beat_fract, note, start_long, end_long, bpm])
        last_time = time_point
        inputs.append(mnd_data)
        outputs.append(out_arr[pos])
        maxouts.append(np.argmax(out_arr[pos],axis=1))
        yield ((np.array(inputs[i]), np.array(maxouts[pos:i])), np.array(outputs[i]))

def metagen(skipname):
    gen = song_data(skipname)
    in_mnd_set = []
    in_hist_set = []
    outL_set = []
    outU_set = []
    outD_set = []
    outR_set = []
    
    while True:
        (name, bpm, (mnd, out)) = next(gen)
        print(name)
        all_data = generate_song_inout_data(mnd, out, bpm)
        (ins, outs) = zip(*all_data)
        (in_mnd, in_hist) = zip(*ins)
        (outL, outU, outD, outR) = zip(*outs)
        in_mnd_set.extend(in_mnd)
        in_hist_set.extend(in_hist)
        outL_set.extend(outL)
        outU_set.extend(outU)
        outD_set.extend(outD)
        outR_set.extend(outR)
        if (len(outL_set) > 6000):
            yield ([in_mnd_set,in_hist_set],[outL_set,outU_set,outD_set,outR_set])
            in_mnd_set = []
            in_hist_set = []
            outL_set = []
            outU_set = []
            outD_set = []
            outR_set = []
    
mgen = metagen(skipname)
while True: #true epoch count AKA number of songs to process
    (ins, outs) = next(mgen)
    model.fit(x=ins, y=outs, batch_size=8192)
    model.save("ddr_model.h5")
    model.save("ddr_modelBACKUP.h5")#save twice so that if you do an interrupt, one is not corrupted
