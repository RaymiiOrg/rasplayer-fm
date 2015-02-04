#!/usr/bin/env python3
# Rasplayer-FM,
# By Remy van Elst, https://raymii.org
# License: GNU GPLv3
# https://raymii.org/s/articles/Raspberry_Pi_FM_Radio_With_Buttons.html
# Inspired by Pirate Radio by Wynter Woods (Make Magazine)

try:	
	import configparser
except: 
	import ConfigParser as configparser
finally:
	import re
	import random
	import sys
	import os
	import threading
	import time
	import subprocess
	import RPi.GPIO as GPIO

cur_song = 0
files_list = []
playing = 0
stop_press = 0

fm_process = None
ffmpeg_process = None
on_off = ["off", "on"]
config_location = "/rasplayerfm/rasplayerfm.conf"

frequency = 108.0
shuffle = False
repeat_all = False
merge_audio_in = False
play_stereo = True
music_dir = "/rasplayerfm"

music_pipe_r,music_pipe_w = os.pipe()

def callback_startstop(channel):
	global files_list
	global cur_song
	global playing
	global stop_press
	if playing:
		if not stop_press:
			print("Stop playback")
			cur_song = cur_song - 1
			kill_ffmpeg_and_pifm()
			stop_press = 1
			playing = 0
	else:
		print("Start playback")
		kill_ffmpeg_and_pifm()
		stop_press = 0


def callback_previous_next(channel):
	global files_list
	global cur_song
	if playing:
		cur_song = cur_song - 1
	kill_ffmpeg_and_pifm()
	if channel == 18:
		if stop_press:
			subprocess.call(["/sbin/shutdown", "-h", "now"])
		cur_song = cur_song - 1
		print("Previous song")
	elif channel == 24:
		cur_song = cur_song + 1
		print("Next song")
	
def add_callbacks():	
	GPIO.add_event_detect(18, GPIO.FALLING, callback=callback_previous_next, bouncetime=300)
	GPIO.add_event_detect(23, GPIO.FALLING, callback=callback_startstop, bouncetime=300)
	GPIO.add_event_detect(24, GPIO.FALLING, callback=callback_previous_next, bouncetime=300)

def setup_gpio():
	GPIO.setmode(GPIO.BCM)
	# button 1, previous
	GPIO.setup(18, GPIO.IN, pull_up_down=GPIO.PUD_UP)
	# button 2, start/stop
	GPIO.setup(23, GPIO.IN, pull_up_down=GPIO.PUD_UP)
	# button 3, next
	GPIO.setup(24, GPIO.IN, pull_up_down=GPIO.PUD_UP)

def main():
	global files_list
	global cur_song
	check_requirements()
	setup_gpio()
	add_callbacks()
	setup()
	if not files_list:
		files_list = build_file_list()
	if shuffle == True:
		random.shuffle(files_list)
	while(True):
		print("main")
		play_song(cur_song)
		time.sleep(1)

def build_file_list():
	file_list = []
	for root, folders, files in os.walk(music_dir):
		folders.sort()
		files.sort()
		for filename in files:
			if re.search(".(aac|mp3|wav|flac|m4a|ogg)$", filename) != None: 
				file_list.append(os.path.join(root, filename))
	if len(file_list) < 1:
		print("Error: no songs found. Add them to %s." % music_dir)
		sys.exit(1)
	return file_list

def kill_ffmpeg_and_pifm():
	global fm_process
	global ffmpeg_process
	global stop_press
	try:
		fm_process.terminate()
		os.wait()
	except Exception as e:
		pass
	
	try:
		ffmpeg_process.kill()
	except Exception as e:
		pass
	playing = 0
	return True

def play_song(song):
	global files_list
	global cur_song
	global playing
	global ffmpeg_process
	kill_ffmpeg_and_pifm()
	if not stop_press:
		print("Number: %i - Name: %s" % (song, files_list[song]))
		playing = 1
		run_pifm()
		with open(os.devnull, "w") as dev_null:
			ffmpeg_process = subprocess.Popen(["ffmpeg","-i",files_list[song],"-f","s16le","-acodec","pcm_s16le","-ac", "2" if play_stereo else "1" ,"-ar","44100","-"],stdout=music_pipe_w, stderr=dev_null)
			ffmpeg_process.wait()
		playing = 0
		cur_song = cur_song + 1

def read_config():
	global frequency
	global shuffle
	global repeat_all
	global play_stereo
	global music_dir
	try:
		config = configparser.ConfigParser()
		config.read(config_location)
		
	except:
		print("Error reading from config file.")
	else:
		play_stereo = config.get("rasplayerfm", 'stereo_playback', fallback=True)
		frequency = config.get("rasplayerfm",'frequency')
		shuffle = config.getboolean("rasplayerfm",'shuffle',fallback=False)
		repeat_all = config.getboolean("rasplayerfm",'repeat_all', fallback=False)
		music_dir = config.get("rasplayerfm", 'music_dir', fallback="/rasplayerfm")
		print("Playing songs to frequency ", str(frequency))
		print("Shuffle is " + on_off[shuffle])
		print("Repeat All is " + on_off[repeat_all])

def setup():
	global frequency
	read_config()
	
def run_pifm(use_audio_in=False):
	global fm_process
	with open(os.devnull, "w") as dev_null:
		fm_process = subprocess.Popen(["/rasplayerfm/pifm","-",str(frequency),"44100", "stereo" if play_stereo else "mono"], stdin=music_pipe_r, stdout=dev_null)

def check_requirements():
	try:
		ffmpeg_check = subprocess.Popen(["ffmpeg", "-v"])
		ffmpeg_check.kill()
	except Exception as e:
		print("Error, please install ffmpeg. I failed it: %s" % e)
		sys.exit(1)
	if not os.path.isfile("/rasplayerfm/pifm"):
		print("Error: pifm binary not found. Please place it in /rasplayerfm/pifm")
		sys.exit(1)
	if not os.path.isfile("/rasplayerfm/rasplayerfm.conf"):
		print("Error: config not found. Please place it in /rasplayerfm/rasplayerfm.conf")
		sys.exit(1)

main()

