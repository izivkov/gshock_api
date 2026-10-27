#! /usr/bin/python
#License: CC0-1.0
# https://creativecommons.org/publicdomain/zero/1.0/

import os
import sys
import struct
from datetime import datetime, timedelta, timezone

DATA_NOT_AVAILABLE = -1

NUM_SLEEP_DATA = 252
SIZE_SLEEP_DATA = 8

cadio_load_status_names = {
	1: "Detraining",
	2: "Maintaining",
	3: "Productive",
	4: "Overreaching",
}

# frame types
FRAME_STEP_COUNTS =      0x50
FRAME_ENERGIES =         0x51
FRAME_HEART_RATES =      0x52
FRAME_SLEEP_PHASE =      0x53
FRAME_BEHAVIOR_PATTERN = 0x56
FRAME_PAST_STAIRS =      0x57
FRAME_BREATH_EXERCISE =  0x58
FRAME_BLOOD_O2_LEVELES = 0x59
FRAME_SLEEP_DATA =       0x5a
FRAME_CARDIO_LOAD =      0x5b
FRAME_SUMMARIES =        0x63
FRAME_CURRENT_STATS =    0x65
FRAME_TYPE_0X72 =        0x72
FRAME_SMART_ALARM =      0x73

class Record_Metadata():
	def __init__(self, record_size, interval, time_unit, parser):
		self.record_size = record_size
		self.unit = time_unit
		self.interval = interval
		self.parser = parser

class Common_Data():
	def __init__(self, time, data, flag):
		self.time = time
		self.data = data
		self.flag = flag

class Stairs_Data():
	def __init__(self, time, climbed, descended, flag):
		self.time = time
		self.climbed = climbed
		self.descended = descended
		self.flag = flag

class Sleep_Phase_Data():
	def __init__(self, time, n_data, data):
		self.time = time
		self.n_data = n_data
		self.data = data

class Heart_Rate_Data():
	def __init__(self, time, heart_rate, flag1, flag2):
		self.time = time
		self.heart_rate = heart_rate
		self.flag1 = flag1
		self.flag2 = flag2

class Type_0x72_Data():
	def __init__(self, time, a, b, c, flag1, flag2, data):
		self.time = time
		self.a = a
		self.b = b
		self.c = c
		self.flag1 = flag1
		self.flag2 = flag2
		self.bindata = data

class Cardio_Load_Data():
	def __init__(self, date, cadio_load, status, strain, tolerance):
		self.date = date
		self.cadio_load = cadio_load
		self.status = status
		self.strain = strain
		self.tolerance = tolerance

class Breathing_Exercise_Data():
	def __init__(self, time_str, measurment_time, optimal, very_good, good):
		self.time = time_str
		self.measurment_time = measurment_time
		self.optimal = optimal
		self.very_good = very_good
		self.good = good

class Summary_Data():
	def __init__(
		self,
		date,
		energy,
		steps,
		step_target,
		step_completion,
		stairs_climbed,
		stairs_descended,
		time_run,
		time_walk,
		time_bike,
		time_zero,
		time_other,
		time_still,
		time_active,
		step_reminder_times,
		num_step_reminder,
		heart_rate_max,
		heart_rate_min,
		heart_rate_rest
	):
		self.date = date
		self.energy = energy
		self.steps = steps
		self.step_target = step_target
		self.step_completion = step_completion
		self.stairs_climbed = stairs_climbed
		self.stairs_descended = stairs_descended
		self.time_run = time_run
		self.time_walk = time_walk
		self.time_bike = time_bike
		self.time_zero = time_zero
		self.time_other = time_other
		self.time_still = time_still
		self.time_active = time_active
		self.step_reminder_times = step_reminder_times
		self.num_step_reminder = num_step_reminder
		self.heart_rate_max = heart_rate_max
		self.heart_rate_min = heart_rate_min
		self.heart_rate_rest = heart_rate_rest

# TODO mark packages with flags other than "20 10"
# TODO mark records after flags other than "20 10"
def parse_flag(data):
	if data == b'\x20\x10':
		flag = "0x2010"
	elif data == b'\xfe\xfe':
		flag = "0xfefe"
	elif data == b'\xf0\x10':
		flag = "0xf010"
	elif data == b'\x24\x10':
		flag = "0x2410"
	else:
		print("Unexpected bytes for flag data: %02x %02x" % (data[0], data[1]), file = sys.stderr)
		flag = "0x" + f'{data[0]:02x}' + f'{data[1]:02x}'

	return flag

def step_count_parser(record):
	flag = parse_flag(record[2:])

	step_count = struct.unpack_from('<H', record)[0]

	return Common_Data("date_unknown", step_count, flag)

def energy_parser(record):
	flag = parse_flag(record[2:])

	energy = struct.unpack_from('<H', record)[0] / 128.0

	return Common_Data("date_unknown", energy, flag)

def heart_rate_parser(record):
	flag2 = parse_flag(record[2:])

	if record[0] == 0xfe:
		heart_rate = DATA_NOT_AVAILABLE
	else:
		heart_rate = struct.unpack_from('<B', record)[0]

	flag1 = struct.unpack_from('<B', record[1:])[0]
	if flag1 != 0xfe and (flag1 % 25 != 0 or flag1 > 100):
		print("Unexpected flag1 for heart rate data:", file = sys.stderr)

	# TODO date-time
	return Heart_Rate_Data("date_unknown", heart_rate, flag1, flag2)

def sleep_phase_parser(record):
	n = 0
	data = []
	# TODO
	for i in range(NUM_SLEEP_DATA):
		tmp = record[i * SIZE_SLEEP_DATA:(i + 1) * SIZE_SLEEP_DATA]

		#print(tmp, file = sys.stderr)
		if i == 0:
			if tmp[6:] != b'\x20\x10':
				print("Unexpected bytes for sleep phase data:", file = sys.stderr)
				print(tmp[6:], file = sys.stderr)

			if tmp == b'\xfe\xfe\xfe\xfe\xfe\xfe\x20\x10':
				valid = False
			else:
				valid = True
				time = ("20" + f'{record[0]:02x}' + "-" +
					f'{record[1]:02x}' + "-" +
					f'{record[2]:02x}' + "_" +
					f'{record[3]:02x}' + ":" +
					f'{record[4]:02x}' + ":" +
					f'{record[5]:02x}')

			continue

		if i == NUM_SLEEP_DATA - 1:
			if tmp != b'\xff\xff\xff\xff\xff\xff\xff\xff':
				print("Unexpected last line for sleep phase data:", file = sys.stderr)

			continue

		if tmp == b'\x00\x00\x00\x00\x00\x00\x00\x00':
			continue

		if tmp[5:] != b'\xff\xff\xff':
			print("Unexpected bytes for sleep phase data:", file = sys.stderr)
			print(tmp[5:], file = sys.stderr)

		seconds = struct.unpack_from('<I', tmp[0:4])[0]

		#0xfe 254 Interuptions
		#0xfd 253 REM
		#0xfb 251 Light
		#0xfa 250 Deep
		if (tmp[4] != 0xfa and tmp[4] != 0xfb and
			tmp[4] != 0xfd and tmp[4] != 0xfe):
			print("Unexpected bytes for sleep phase type:", file = sys.stderr)
			print(tmp[4], file = sys.stderr)

		flag = struct.unpack_from('<B', tmp[4:])[0]

		data_point = {}
		data_point[seconds] = flag

		data.append(data_point)
		n = n + 1

	if valid == False:
		if n > 0:
			print("Unexpected data for sleep phase data:", file = sys.stderr)

		return None

	if valid == True:
		return Sleep_Phase_Data(time, n, data)

def behavior_pattern_parser(record):
	flag = parse_flag(record[1:])

	# TODO check values
#     0xa0 160~162 => running???
#  >= 0x80 128~130 => walk???
#     0x60 96~98   => bike???
#     0x0  0       => display powersave???(not all display powersave are always 0???)
#     0x10 16      => no movement???
#     0x20 32      => little movement???
#          254     => manual powersave/battery LOW?
#          4       => ???
	behavior_pattern = struct.unpack_from('<B', record)[0]

	# TODO date-time
	return Common_Data("date_unknown", behavior_pattern, flag)

def past_stairs_parser(record):
	flag = parse_flag(record[6:8])

	time_str = ("20" + f'{record[0]:02x}' + "-" + f'{record[1]:02x}' + "-" +
                    f'{record[2]:02x}' + "_" + f'{record[3]:02x}' + ":" +
                    f'{record[4]:02x}' + ":" + f'{record[5]:02x}')

	climbed = struct.unpack_from('<B', record[8:])[0]
	descended = struct.unpack_from('<B', record[10:])[0]

	return Stairs_Data(time_str, climbed, descended, flag)

def breath_exercise_parser(record):
	time_str = ("20" + f'{record[0]:02x}' + "-" + f'{record[1]:02x}' + "-" +
                    f'{record[2]:02x}' + "_" + f'{record[3]:02x}' + ":" +
                    f'{record[4]:02x}')

	if record[5] != 0x20:
		print("Unexpected byte[5] for breath exercise data: %02x" % (record[5]), file = sys.stderr)

	measurment_time = f'{record[6]:02x}' + ":" f'{record[7]:02x}'
	optimal = f'{record[8]:02x}' + ":" f'{record[9]:02x}'
	very_good = f'{record[10]:02x}' + ":" f'{record[11]:02x}'
	good = f'{record[12]:02x}' + ":" f'{record[13]:02x}'

	if record[14] != 0x10:
		print("Unexpected last byte for breath exercise data", file = sys.stderr)

	return Breathing_Exercise_Data(time_str, measurment_time, optimal, very_good, good)

def blood_O2_leveres_parser(record):
	time_str = ("20" + f'{record[0]:02x}' + "-" + f'{record[1]:02x}' + "-" +
                    f'{record[2]:02x}' + "_" + f'{record[3]:02x}' + ":" +
                    f'{record[4]:02x}')

	if record[5] != 0x20:
		print("Unexpected byte[5] for blood oxygen level: %02x" % (record[5]), file = sys.stderr)

	bload_O2_level = record[6]

	# XXX
	# TODO return record[7]
	if record[7:] != b'\x03\x00\x10' and record[7:] != b'\x04\x00\x10':
		print("Unexpected tailing bytes for blood oxygen level", file = sys.stderr)

	return Common_Data(time_str, bload_O2_level, 0)

def sleep_data_parser(record):
	# TODO
	date_str = ("20" + f'{record[0]:02x}' + "-" + f'{record[1]:02x}' + "-" +
                    f'{record[2]:02x}')

	# FIXME
	return Common_Data(date_str, 0, 0)

def cardio_load_parser(record):
	# TODO
	# XXX discrepancy between date_str and CASIO WATCHES
	date_str = ("20" + f'{record[0]:02x}' + "-" + f'{record[1]:02x}' + "-" +
                    f'{record[2]:02x}')

	if record[3:] == b'\x20\xfe\xff\xff\xff\xfe\xfe\xff\xfe\xff\x10':
		#return None
		return Cardio_Load_Data(date_str, float('nan'), DATA_NOT_AVAILABLE, DATA_NOT_AVAILABLE, DATA_NOT_AVAILABLE)

	if record[3] != 0x20:
		print("Unexpected byte[3] for cardio load data: %02x" % (record[3]), file = sys.stderr)

	cadio_load = struct.unpack_from('<f', record[4:])[0]

	status = record[8]
	if status not in cadio_load_status_names:
		print("Unexpected cardio load status: %02x" % (status), file = sys.stderr)

	strain = struct.unpack_from('<H', record[9:])[0]
	tolerance = struct.unpack_from('<H', record[11:])[0]

	if record[13] != 0x10:
		print("Unexpected byte[13] for cardio load data: %02x" % (record[13]), file = sys.stderr)

	return Cardio_Load_Data(date_str, cadio_load, status, strain, tolerance)

def summary_parser(record):
	time_str = ("20" + f'{record[0]:02x}' + "-" + f'{record[1]:02x}' + "-" +
                    f'{record[2]:02x}')
	# TODO

	if record[3] != 0x20:
		print("Unexpected byte[3] for daily summary data: %02x" % (record[3]), file = sys.stderr)

	if record[4] != 0x5d:
		print("Unexpected byte[4] for daily summary data: %02x" % (record[4]), file = sys.stderr)

	energy = struct.unpack_from('<i', record[5:])[0] / 128.0

	if record[9] != 0x5c:
		print("Unexpected byte[9] for daily summary data: %02x" % (record[9]), file = sys.stderr)

	steps = struct.unpack_from('<i', record[10:])[0]
	step_target = struct.unpack_from('<i', record[14:])[0]
	# percentage of steps to step_target
	step_completion = struct.unpack_from('<H', record[18:])[0]

	if record[20] != 0x60:
		print("Unexpected byte[20] for daily summary data: %02x" % (record[20]), file = sys.stderr)

	stairs_climbed = struct.unpack_from('<H', record[21:])[0]
	stairs_descended = struct.unpack_from('<H', record[23:])[0]

	if record[25] != 0x62:
		print("Unexpected byte[25] for daily summary data: %02x" % (record[25]), file = sys.stderr)

	# TODO
	time_run = record[26] * 3600 + record[27] * 60 + record[28]
	time_walk = record[29] * 3600 + record[30] * 60 + record[31]
	time_bike = record[32] * 3600 + record[33] * 60 + record[34]
	time_zero = record[35] * 3600 + record[36] * 60 + record[37]
	time_other = record[38] * 3600 + record[39] * 60 + record[40]
	time_still = record[41] * 3600 + record[42] * 60 + record[43]
	time_active = record[44] * 3600 + record[45] * 60 + record[46]

	if time_zero != 0:
		print("Unexpected time_zero for daily summary data: %d" % (time_zero), file = sys.stderr)

	if time_active != time_run + time_walk + time_bike + time_zero + time_other:
		print("daily summary data: time_active is not equal to sum(time_activities)", file = sys.stderr)

	if record[47] != 0xff:
		print("Unexpected byte[48] for daily summary data: %02x" % (record[48]), file = sys.stderr)

	if record[48] != 0x61:
		print("Unexpected byte[48] for daily summary data: %02x" % (record[48]), file = sys.stderr)

	step_reminder_times = []
	n_not_fefe = 0
	for i in range(24):
		step_reminder_times.append(f'{record[49 + 2 * i + 1]:02x}'
			+ ":" + f'{record[49 + 2 * i]:02x}')

		if record[49 + 2 * i + 1] != 0xfe and record[49 + 2 * i] != 0xfe:
			n_not_fefe = n_not_fefe + 1

	num_step_reminder = record[97]
	if num_step_reminder != n_not_fefe:
		print("Inconsistence in step reminder data in daily summary data", file = sys.stderr)

	if record[98] != 0xff:
		print("Unexpected byte[99] for daily summary data: %02x" % (record[99]), file = sys.stderr)

	if record[99] != 0x5e:
		print("Unexpected byte[99] for daily summary data: %02x" % (record[99]), file = sys.stderr)

	if record[100:102] == b'\xfe\xff':
		heart_rate_max = DATA_NOT_AVAILABLE
	else:
		heart_rate_max = struct.unpack_from('<H', record[100:])[0]

	if record[102:104] == b'\xfe\xff':
		heart_rate_min = DATA_NOT_AVAILABLE
	else:
		heart_rate_min = struct.unpack_from('<H', record[102:])[0]

	if record[104:106] == b'\xfe\xff':
		heart_rate_rest = DATA_NOT_AVAILABLE
	else:
		heart_rate_rest = struct.unpack_from('<H', record[104:])[0]

	if record[106:] != b'\x64\x00\x00':
		print("Unexpected byte[106:] for daily summary data: %02x %02x %02x" % (record[106], record[107], record[108]), file = sys.stderr)

	return Summary_Data(
		time_str,
		energy,
		steps,
		step_target,
		step_completion,
		stairs_climbed,
		stairs_descended,
		time_run,
		time_walk,
		time_bike,
		time_zero,
		time_other,
		time_still,
		time_active,
		step_reminder_times,
		num_step_reminder,
		heart_rate_max,
		heart_rate_min,
		heart_rate_rest
	)

def current_stats_parser(record):
	# TODO
	time_str = "undefined"
	energy = -1
	steps = -1
	step_target = -1
	step_completion = -1

	if record[0] != 0x5b:
		print("Unexpected byte[0] for daily summary data: %02x" % (record[0]), file = sys.stderr)

	# cardio load

	if record[10] != 0x60:
		print("Unexpected byte[10] for daily summary data: %02x" % (record[10]), file = sys.stderr)

	stairs_climbed = struct.unpack_from('<H', record[11:])[0]
	stairs_descended = struct.unpack_from('<H', record[13:])[0]

	if record[15] != 0x62:
		print("Unexpected byte[15] for daily summary data: %02x" % (record[15]), file = sys.stderr)

	# TODO
	time_run = record[16] * 3600 + record[17] * 60 + record[18]
	time_walk = record[19] * 3600 + record[20] * 60 + record[21]
	time_bike = record[22] * 3600 + record[23] * 60 + record[24]
	time_zero = record[25] * 3600 + record[26] * 60 + record[27]
	time_other = record[28] * 3600 + record[29] * 60 + record[30]
	time_still = record[31] * 3600 + record[32] * 60 + record[33]
	time_active = record[34] * 3600 + record[35] * 60 + record[36]

	if time_zero != 0:
		print("Unexpected time_zero for daily summary data: %d" % (time_zero), file = sys.stderr)

	if time_active != time_run + time_walk + time_bike + time_zero + time_other:
		print("daily summary data: time_active is not equal to sum(time_activities)", file = sys.stderr)

	if record[37] != 0x61:
		print("Unexpected byte[37] for daily summary data: %02x" % (record[37]), file = sys.stderr)

	step_reminder_times = []
	n_not_fefe = 0
	for i in range(24):
		step_reminder_times.append(f'{record[38 + 2 * i + 1]:02x}'
			+ ":" + f'{record[38 + 2 * i]:02x}')

		if record[38 + 2 * i + 1] != 0xfe and record[38 + 2 * i] != 0xfe:
			n_not_fefe = n_not_fefe + 1

	num_step_reminder = record[86]
	if num_step_reminder != n_not_fefe:
		print("Inconsistence in step reminder data in daily summary data", file = sys.stderr)

	if record[87] != 0x5e:
		print("Unexpected byte[87] for daily summary data: %02x" % (record[87]), file = sys.stderr)

	if record[88:90] == b'\xfe\xff':
		heart_rate_max = DATA_NOT_AVAILABLE
	else:
		heart_rate_max = struct.unpack_from('<H', record[88:])[0]

	if record[90:92] == b'\xfe\xff':
		heart_rate_min = DATA_NOT_AVAILABLE
	else:
		heart_rate_min = struct.unpack_from('<H', record[90:])[0]

	if record[92:94] == b'\xfe\xff':
		heart_rate_rest = DATA_NOT_AVAILABLE
	else:
		heart_rate_rest = struct.unpack_from('<H', record[92:])[0]

	return Summary_Data(
		time_str,
		energy,
		steps,
		step_target,
		step_completion,
		stairs_climbed,
		stairs_descended,
		time_run,
		time_walk,
		time_bike,
		time_zero,
		time_other,
		time_still,
		time_active,
		step_reminder_times,
		num_step_reminder,
		heart_rate_max,
		heart_rate_min,
		heart_rate_rest
	)

def type_0x72_parser(record):
	a = 0
	b = 0
	c = 0

	flag1 = parse_flag(record[5:7])

	# TODO
	time_str = ("20" + f'{record[0]:02x}' + "-" + f'{record[1]:02x}' + "-" +
                    f'{record[2]:02x}' + "_" + f'{record[3]:02x}' + ":" +
                    f'{record[4]:02x}')

	if record[7:] == b'\x80\x80\x80\x80\x80\x80\x80\x80\x80\xff\xff\xff\x00\x00\x00\x00\xff\xff\xff\xff\xff\xff\xff\xff\xff':
		flag2 = 8
	elif record[7:] == b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00':
		flag2 = 0
	elif record[7:] == b'\xfe\xfe\xfe\xfe\xfe\xfe\xfe\xfe\xfe\xfe\xfe\xfe\xfe\xfe\xff\xfe\xff\xfe\xfe\xfe\xfe\xfe\xfe\xfe\xfe':
		flag2 = 254
	else:
		a = struct.unpack_from('<b', record[7:])[0]
		b = struct.unpack_from('<b', record[8:])[0]
		c = struct.unpack_from('<b', record[9:])[0]

		#print(time_str)
		#sys.stdout.buffer.write(record[7:])
		#print("%d %d %d" % (struct.unpack_from('<b', record[13:])[0], struct.unpack_from('<b', record[14:])[0], struct.unpack_from('<b', record[15:])[0]))
#struct.unpack_from('<b', record[7:])[0] - struct.unpack_from('<b', record[13:])[0], struct.unpack_from('<b', record[8:])[0] - struct.unpack_from('<b', record[14:])[0], struct.unpack_from('<b', record[9:])[0] - struct.unpack_from('<b', record[15:])[0]))

		#flag2 = 10000 + record[20]
		flag2 = 1
		#flag2 = 10000 + struct.unpack_from('<B', record[29:])[0]

		if record[18] != 0x0:
			print("Unexpected byte[18] for type 0x72 data: %02x" % (record[18]), file = sys.stderr)

	return Type_0x72_Data(time_str, a, b, c, flag1, flag2, record[7:])

def smart_alarm_parser(record):
	# TODO
	time_str = ("20" + f'{record[0]:02x}' + "-" + f'{record[1]:02x}' + "-" +
                    f'{record[2]:02x}' + "_" + f'{record[3]:02x}' + ":" +
                    f'{record[4]:02x}' + ":" + f'{record[5]:02x}')

	if record[6:8] != b'\x20\x10':
		print("Unexpected bytes[6:8] for type 0x73 data", file = sys.stderr)

	if record[13] != 0x02:
		print("Unexpected bytes[13] for type 0x73 data", file = sys.stderr)

	if record[18] != 0x02:
		print("Unexpected bytes[18] for type 0x73 data", file = sys.stderr)

	# XXX
	print("0x73 %s " % (time_str), end='')

	# XXX
	for j in range(6, 19):
		print("%02x " % (record[j]), end='')
		#print("%d " % (record[j]), end='')

	sound_time = (f'{record[22]:02x}' + ":" + f'{record[23]:02x}' + ":" +
		f'{record[24]:02x}')

	# XXX
	print("%s" % (sound_time))

	return

frame_types = {
	FRAME_STEP_COUNTS:      Record_Metadata(4, 5, "min", step_count_parser),
	FRAME_ENERGIES:         Record_Metadata(4, 5, "min", energy_parser),
	FRAME_HEART_RATES:      Record_Metadata(4, 2, "min", heart_rate_parser),
	FRAME_SLEEP_PHASE:      Record_Metadata(2016, 1, "day", sleep_phase_parser),
	FRAME_BEHAVIOR_PATTERN: Record_Metadata(3, 1, "min", behavior_pattern_parser),
	FRAME_PAST_STAIRS:      Record_Metadata(12, 0, "vary", past_stairs_parser),
	FRAME_BREATH_EXERCISE:  Record_Metadata(15, 0, "vary", breath_exercise_parser),
	FRAME_BLOOD_O2_LEVELES: Record_Metadata(10, 0, "vary", blood_O2_leveres_parser),
	FRAME_SLEEP_DATA:       Record_Metadata(55, 1, "day", sleep_data_parser),
	FRAME_CARDIO_LOAD:      Record_Metadata(14, 1, "day", cardio_load_parser),
	FRAME_SUMMARIES:        Record_Metadata(109, 1, "day", summary_parser),
	FRAME_CURRENT_STATS:    Record_Metadata(94, 0, "current", current_stats_parser),
	FRAME_TYPE_0X72:        Record_Metadata(32, 5, "min", type_0x72_parser),
	FRAME_SMART_ALARM:      Record_Metadata(395, 0, "vary", smart_alarm_parser),
}

def parse_frame(type, length, body, package):
	if type not in frame_types:
		print("Unexpected frame type: 0x%02x" % (type), file = sys.stderr)

		return

	# FIXME
	#if (type == FRAME_CURRENT_STATS or type == FRAME_SMART_ALARM):
	#if (type == FRAME_CURRENT_STATS):
		#return

	record_size = frame_types[type].record_size

	if record_size != 0 and length % record_size != 0:
		print("Irregular frame size for frame type: 0x%02x" % (type), file = sys.stderr)

		return

	result = []

	rest = body

	while len(rest) > 0:
		record = rest[:record_size]

		returned = frame_types[type].parser(record)
		if returned is not None:
			result.append(returned)

		rest = rest[record_size:]

	if type in package:
		print("Find multiple frames of the same type", file = sys.stderr)

		return

	package[type] = result

file_path = sys.argv[1]

header_size = 20
frame_header_size = 5

file_size = os.path.getsize(file_path)

if file_size < 119:
	print("The filesize is smaller than 119 bytes; frame 0x65 is missing or truncated.", file = sys.stderr)

DIFF_FILE_SIZE_PAYLOAD_LENGTH = 14

with open(file_path, 'rb') as f:
	chunk = f.read(header_size)
	# TODO check len(chunk)

	if chunk[0:5] != b'\x00\x0f\x00\x00\x00':
		print("Unexpected values of the first 5 bytes", file = sys.stderr)

	package_time_str = f"20{chunk[5]:02d}-{chunk[6]:02d}-{chunk[7]:02d}_{chunk[8]:02d}:{chunk[9]:02d}"
	package_time = datetime(year = 2000 + chunk[5], month = chunk[6],
		day = chunk[7], hour = chunk[8], minute = chunk[9], tzinfo=timezone.utc)

	payload_length = struct.unpack_from('<i', chunk[10:])[0]

	if payload_length + DIFF_FILE_SIZE_PAYLOAD_LENGTH != file_size:
		print("Unexpected payload length: %d" % (file_size - DIFF_FILE_SIZE_PAYLOAD_LENGTH), file = sys.stderr)
		print("Expecting: %d" % (payload_length), file = sys.stderr)

	# today's current step count
	current_steps = struct.unpack_from('<i', chunk[14:])[0]
	# today's current energy in kcal
	current_energy = struct.unpack_from('<H', chunk[18:])[0]

	print("0x00 %s %d %d" % (package_time_str, current_steps, current_energy))

	package = {}

	while True:
		chunk = f.read(frame_header_size)
		if not chunk:
			break

		frame_type = chunk[0]

		frame_length = struct.unpack_from('<i', chunk[1:])[0]

		body_length = frame_length - frame_header_size
		frame_body = f.read(body_length)

		if len(frame_body) != body_length:
			print("Reached EOF before parsing completes", file = sys.stderr)

			break


		# XXX
		print('type-len 0x%02x %d' % (frame_type, frame_length))

		parse_frame(frame_type, body_length, frame_body, package)

	if FRAME_TYPE_0X72 in package:
		# TODO fix time for display powersave
		# TODO check flag consistence between all 3 records
		if len(package[FRAME_TYPE_0X72]) != len(package[FRAME_STEP_COUNTS]):
			print("Number of records for step counts not equal to that for type 0x72", file = sys.stderr)

		#for i in range(len(package[FRAME_TYPE_0X72])):
		# FIXME
		for i in range(len(package[FRAME_STEP_COUNTS])):
			package[FRAME_STEP_COUNTS][i].time = package[FRAME_TYPE_0X72][i].time

			record = package[FRAME_STEP_COUNTS][i]
			print("0x50 %s %d %s" % (record.time, record.data, record.flag))

		if len(package[FRAME_TYPE_0X72]) != len(package[FRAME_ENERGIES]):
			print("Number of records for energies not equal to that for type 0x72", file = sys.stderr)

		for i in range(len(package[FRAME_TYPE_0X72])):
			package[FRAME_ENERGIES][i].time = package[FRAME_TYPE_0X72][i].time

			record = package[FRAME_ENERGIES][i]
			print("0x51 %s %f %s" % (record.time, record.data, record.flag))

		time_last = package[FRAME_ENERGIES][0].time
		time_first = package[FRAME_ENERGIES][-1].time
		n_type_0x72 = len(package[FRAME_TYPE_0X72])

	else:
		time_last = "_______________"
		time_first = "_______________"
		n_type_0x72 = 0

	if FRAME_HEART_RATES in package:
		n_heart_rates = len(package[FRAME_HEART_RATES])

		if package_time.minute % 2 == 1:
			minute_offset = 1
		else:
			minute_offset = 0

		for i in range(n_heart_rates):
			delta = timedelta(minutes = i * frame_types[FRAME_HEART_RATES].interval + minute_offset)
			package[FRAME_HEART_RATES][i].time = package_time - delta

			record = package[FRAME_HEART_RATES][i]
			print("0x52 %s %d %d %s" % (record.time.strftime("%Y-%m-%d_%H:%M"), record.heart_rate, record.flag1, record.flag2))
	else:
		n_heart_rates = 0

	if FRAME_BEHAVIOR_PATTERN in package:
		n_active = len(package[FRAME_BEHAVIOR_PATTERN])

		for i in range(n_active):
			delta = timedelta(minutes = i * frame_types[FRAME_BEHAVIOR_PATTERN].interval)
			package[FRAME_BEHAVIOR_PATTERN][i].time = package_time - delta

			record = package[FRAME_BEHAVIOR_PATTERN][i]
			print("0x56 %s %d %s" % (record.time.strftime("%Y-%m-%d_%H:%M"), record.data, record.flag))
	else:
		n_active = 0

#	print("%s %s %s %d %d %d" % (
#		package_time_str, 
#		time_last,
#		time_first,
#		n_type_0x72,
#		n_heart_rates,
#		n_active))

	if FRAME_PAST_STAIRS in package:
		for data_point in package[FRAME_PAST_STAIRS]:
			print("0x57 %s %d %d %s" % (data_point.time, data_point.climbed, data_point.descended, data_point.flag))

	if FRAME_BREATH_EXERCISE in package:
		for data_point in package[FRAME_BREATH_EXERCISE]:
			print("0x58 %s %s %s %s %s" % (
				data_point.time,
				data_point.measurment_time,
				data_point.optimal,
				data_point.very_good,
				data_point.good))

	if FRAME_BLOOD_O2_LEVELES in package:
		for data_point in package[FRAME_BLOOD_O2_LEVELES]:
			print("0x59 %s %d" % (data_point.time, data_point.data))

	if FRAME_SLEEP_PHASE in package:
		for segment in package[FRAME_SLEEP_PHASE]:
			if segment == None:
				continue

			time = segment.time

			# FIXME
			for i in range(segment.n_data):
				for seconds, flag in segment.data[i].items():
					print("0x53 %s %d %d" % (time, seconds, flag))

	if FRAME_SLEEP_DATA in package:
		for data_point in package[FRAME_SLEEP_DATA]:
			# TODO
			print("0x5a %s" % (data_point.time))


	if FRAME_CARDIO_LOAD in package:
		for data_point in package[FRAME_CARDIO_LOAD]:
			print("0x5b %s %f %d %d %d" % (
				data_point.date,
				data_point.cadio_load,
				data_point.status,
				data_point.strain,
				data_point.tolerance))

	if FRAME_SUMMARIES in package:
		for data_point in package[FRAME_SUMMARIES]:
			# TODO
			print("0x63 %s %f %d %d %d %d %d %d %d %d %d %d %d %d %d %d %d %d" %
				(
				data_point.date,
				data_point.energy,
				data_point.steps,
				data_point.step_target,
				data_point.step_completion,
				data_point.stairs_climbed,
				data_point.stairs_descended,
				data_point.time_run,
				data_point.time_walk,
				data_point.time_bike,
				data_point.time_zero,
				data_point.time_other,
				data_point.time_still,
				data_point.time_active,
				data_point.num_step_reminder,
				data_point.heart_rate_max,
				data_point.heart_rate_min,
				data_point.heart_rate_rest,
				)
			)

			for i in range(data_point.num_step_reminder):
				# XXX date 
				if data_point.step_reminder_times[i] != "fe:fe":
					print("0x6361 %s %s" % (data_point.date, data_point.step_reminder_times[i]))

	if FRAME_CURRENT_STATS in package:
		for data_point in package[FRAME_CURRENT_STATS]:
			# TODO cardio load
			print("0x65 %s %d %d %d %d %d %d %d %d %d %d %d %d %d" %
				(
				package_time_str,
				data_point.stairs_climbed,
				data_point.stairs_descended,
				data_point.time_run,
				data_point.time_walk,
				data_point.time_bike,
				data_point.time_zero,
				data_point.time_other,
				data_point.time_still,
				data_point.time_active,
				data_point.num_step_reminder,
				data_point.heart_rate_max,
				data_point.heart_rate_min,
				data_point.heart_rate_rest,
				)
			)

			for i in range(data_point.num_step_reminder):
				# XXX date 
				if data_point.step_reminder_times[i] != "fe:fe":
					print("0x6561 %s %s" % (package_time_str, data_point.step_reminder_times[i]))

	if FRAME_TYPE_0X72 in package:
		for i in range(n_type_0x72):
			record = package[FRAME_TYPE_0X72][i]
			#print("0x72 %s %d %d %d " % (record.time, record.a, record.b, record.c), end='')
			#print("%d %d %d " % (record.bindata[3], record.bindata[4], record.bindata[5]), end='')
			#for j in range(6, 9):
			#	byte = struct.unpack_from('<b', record.bindata[j:])[0]
			#	print("%d " % (byte), end='')
			#for j in range(9, 25):
			#	print("%d " % (record.bindata[j]), end='')
			#print("%s %d" % (record.flag1, record.flag2))

			print("0x72-step-energy %s %d %d %d " % (record.time, record.a, record.b, record.c), end='')
			print("%d %d %d " % (record.bindata[3], record.bindata[4], record.bindata[5]), end='')
			for j in range(6, 9):
				byte = struct.unpack_from('<b', record.bindata[j:])[0]
				print("%d " % (byte), end='')
			for j in range(9, 25):
				print("%d " % (record.bindata[j]), end='')
			# XXX
			if i < len(package[FRAME_STEP_COUNTS]):
				step_counts = package[FRAME_STEP_COUNTS][i].data
			else:
				step_counts = -1

			print("%s %d %d %f" % (record.flag1, record.flag2, step_counts, package[FRAME_ENERGIES][i].data))
