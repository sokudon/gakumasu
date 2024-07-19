#original src https://obsproject.com/forum/resources/date-time.906/
#py -m pip install python-dateutil

# 導入手順　https://photos.app.goo.gl/puPDpiXsFb41YjW77
#work on OBS  python312
#2024/07/20　UTCMATERにM$の標準時リストUTC+??を追加  zoneinfoからの全取得コードを追加（デフォは57行コメントアウト）,開始終了時刻がどちらかが未確定のときエラーを減らした
#2024/06/08　ISO8601以外の通常の時刻を変換できるようにした　例:2024/06/08 03:28
#2024/05/21　zoneinfoのデータが2006年前でしかはいってないようなので除外（）
#2024/05/16 開始の変換でzone影響あり　tzdataからpythondateutil　変更
#2024/05/16 ISO8601でのイベントタイマーに改造

import obspython as obs
import datetime
import math
import time
from dateutil import tz
import re

#書式コード	説明	例 ゾーン影響あり
#%Y	西暦（4桁表記。0埋め）	2021
#%m	月（2桁表記。0埋め）	11
#%d	日（2桁表記。0埋め）	04
#%H	時（24時間制。2桁表記。0埋め）	17
#%M	分（2桁表記。0埋め）	37
#%S	秒（2桁表記。0埋め）	28
#%y	西暦の下2桁（0埋め）	21
#%l	AM／PMを表す文字列	PM
#%x	日付をMM/DD/YY形式にしたもの	11/04/21
#%X	時刻をhh:mm:ss形式にしたもの	17:37:28
#%a	曜日の短縮形	Thu
#%A	曜日	Thursday
#%z	現在のタイムゾーンとUTC（協定世界時）とのオフセット	+0900
#%Z	現在のタイムゾーン	JST

##拡張部分 ゾーン影響なし
#OS %OS　　awareなんでタイムゾーンは欠損　time_formatで出力
#JST %JST　　日本時間time_formatで出力　常にGMT＋９
#UTC %UTC　　UTC MASTER  time_formatで出力
#ZULL %ZULL　UTC協定時間 ISO8601
#ISO %ISO　　zone影響あり ISO8601
#
#イベント名:%E
#開始時刻:%ST　zone影響あり
#終了時刻:%EN　zone影響あり
#イベ期間:%SP
#経過時間:%EL
#残り時間:%LF
#進捗状況:%Q %P%%

interval	= 10  #更新間隔0.1秒
source_name = ""
time_string = "%Y/%m/%d %H:%M:%S %z"
time_format = "%Y/%m/%d %H:%M:%S %Z %a"
iso_format = "%Y-%m-%dT%H:%M:%S%z"
zone		="Asia/Tokyo"

# 全てのタイムゾーンを取得を使いたい場合下のコード
#おそらくzoneinfoのインストールが必要　　python -m pip install tzdata
from zoneinfo import available_timezones
zones = sorted(available_timezones())
#zones	   = ["Asia/Tokyo","Asia/Seoul","Asia/Taipei","America/Los_Angeles"]

#https://learn.microsoft.com/ja-jp/windows-hardware/manufacture/desktop/default-time-zones?view=windows-11
mstz = ["UTC-11:00","UTC-10:00","UTC-08:00","UTC-07:00","UTC-06:00","UTC-05:00","UTC-04:30","UTC-04:00","UTC-03:00","UTC-02:00","UTC-01:00","UTC","UTC+01:00","UTC+02:00","UTC+03:00","UTC+03:30","UTC+04:00","UTC+04:30","UTC+05:00","UTC+05:30","UTC+05:45","UTC+06:00","UTC+06:30","UTC+07:00","UTC+08:00","UTC+09:00","UTC+10:00","UTC+11:00","UTC+12:00","UTC+13:00"]



ibe='星雲の窓辺'
st = '2024-04-30T17:00:00+09:00'
en = '2024-05-08T22:00:00+09:00'
obsbar =3
utc =9
JST=""
UTC=""
# Regular expression patterns for the various formats
patterns = [
	r"^\d{4}/\d{2}/\d{2} \d{2}:\d{2}$",		   # YYYY/MM/DD HH:MM
	r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$",		   # YYYY/MM/DD HH:MM
	r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$",	  # YYYY-MM-DDTHH:MM:SS
	r"^\d{4}/\d{2}/\d{2}$",						# YYYY/MM/DD
	r"^\d{4}-\d{2}-\d{2}$",						 # YYYY-MM-DD
	r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[\+\-]\d{2}:\d{2})?$"
]

# ------------------------------------------------------------


def dtime(dt):
	if dt<0:
			return "0日0時間0分"
	dt=abs(dt)
	seconds  = math.floor((dt / 10) % 60)
	minutes  = math.floor((dt / 60) % 60)
	hours	= math.floor((dt / 3600) % 24)
	days	 = math.floor(dt / 86400)
	tmp = str(days) +"日" +str(hours)+"時間"+str(minutes) +"分"
	return tmp


def makebar(p):
	global obsbar
	
	base ="="
	q=obsbar
	
	p=p/q
	
	p=math.floor(p)
	s=""
	
	for i in range(p):
		s= s + base
		
	s=s+">"
	
	q=math.floor(100/q)
	for i in range(p+1,q, 1):
		s= s +"_"

	bar = "["+s+"]"
	return bar


def update_text():
	global interval
	global source_name
	global time_string
	global time_format
	global zone
	global ibe
	global st
	global en
	global iso_format
	global UTC
	global JST
	
	# 変換前後のタイムゾーンを指定
	cv_tz = tz.gettz(zone)
	temp=time_string
	nn=time.time()
	if(st != "----"):
		stt  = datetime.datetime.fromisoformat(st)
		stt = stt.astimezone(cv_tz)
		ts = stt.strftime(time_format)
		sttmp=stt.timestamp()
		stt=datetime.datetime.fromtimestamp(sttmp)
		elapsed=dtime(nn-sttmp)
		temp=temp.replace('%ST',ts)
		temp=temp.replace('%EL',elapsed)
	else:
		temp=temp.replace('%EL',"----")
		temp=temp.replace('%ST',"----")
	
	if(en != "----"):
		ent  = datetime.datetime.fromisoformat(en)
		ent = ent.astimezone(cv_tz)
		te = ent.strftime(time_format)
		entmp=ent.timestamp()
		ent=datetime.datetime.fromtimestamp(entmp)
		left= dtime(entmp-nn)
		temp=temp.replace('%EN',te)
		temp=temp.replace('%LF',left)
		if(st != "----"):
			span= abs(ent-stt)
			x = (nn-sttmp)/abs(entmp-sttmp)*100
			n = 2
			y = math.floor(x * 10 ** n) / (10 ** n)
			if y>100:
					 y=100
			if y<0:
					 y=0
			bar=makebar(y)
			temp=temp.replace('%SP',str(span))
			temp=temp.replace('%Q',bar)
			temp=temp.replace('%P',str(y))
	else:
		temp=temp.replace('%EN',"----")
		temp=temp.replace('%LF',"----")

	temp=temp.replace('%E',ibe)
	temp=temp.replace('%OS',datetime.datetime.now(tz=None).strftime(time_format))
	temp=temp.replace('%JST',datetime.datetime.now(JST).strftime(time_format))
	temp=temp.replace('%UTC',datetime.datetime.now(UTC).strftime(time_format))
	temp=temp.replace('%ZULL',datetime.datetime.now(datetime.timezone.utc).strftime(iso_format))
	temp=temp.replace('%ISO',datetime.datetime.now().astimezone(cv_tz).strftime(iso_format))
	temp=re.sub('%(P|Q|SP)', '----', temp)

	source = obs.obs_get_source_by_name(source_name)
	if source is not None:
		settings = obs.obs_data_create()
		now = datetime.datetime.now()
		now=now.astimezone(cv_tz)
		obs.obs_data_set_string(settings, "text", now.strftime(temp))
		obs.obs_source_update(source, settings)
		obs.obs_data_release(settings)
		obs.obs_source_release(source)

def refresh_pressed(props, prop):
	update_text()

# ------------------------------------------------------------

def script_description():
	return "Updates a text source to the current date and time"

def script_defaults(settings):
	obs.obs_data_set_default_int(settings, "interval", interval)
	obs.obs_data_set_default_string(settings, "utc","UTC")
	obs.obs_data_set_default_string(settings, "format", time_string)
	obs.obs_data_set_default_string(settings, "time_format", time_format)
	obs.obs_data_set_default_string(settings, "zone", zone )
	obs.obs_data_set_default_string(settings, "eve", ibe)
	obs.obs_data_set_default_string(settings, "start", st)
	obs.obs_data_set_default_string(settings, "end", en)
	obs.obs_data_set_default_int(settings, "bar", obsbar)

def script_properties():
	props = obs.obs_properties_create()

	obs.obs_properties_add_int(props, "interval", "Update Interval (seconds)", 1, 3600, 1)


	# Add sources select dropdown
	p = obs.obs_properties_add_list(props, "source", "Text Source", obs.OBS_COMBO_TYPE_EDITABLE, obs.OBS_COMBO_FORMAT_STRING)

	# Make a list of all the text sources
	obs.obs_property_list_add_string(p, "[No text source]", "[No text source]")
	
	sources = obs.obs_enum_sources()

	if sources is not None:
		for source in sources:
			name = obs.obs_source_get_name(source)
			source_id = obs.obs_source_get_unversioned_id(source)
			if source_id == "text_gdiplus" or source_id == "text_ft2_source":
				name = obs.obs_source_get_name(source)
				obs.obs_property_list_add_string(p, name, name)
		obs.source_list_release(sources)

	mstime_zone_list = obs.obs_properties_add_list(
		props, "utc", "UTC MASTER", obs.OBS_COMBO_TYPE_LIST, obs.OBS_COMBO_FORMAT_STRING
	)

	for mszone in mstz:
		obs.obs_property_list_add_string(mstime_zone_list, mszone, mszone)
		
		
	time_zone_list = obs.obs_properties_add_list(
		props, "zone", "Time zone", obs.OBS_COMBO_TYPE_LIST, obs.OBS_COMBO_FORMAT_STRING
	)

	for timezone in zones:
		obs.obs_property_list_add_string(time_zone_list, timezone, timezone)
	
	obs.obs_properties_add_text(props, "format", "time_string", obs.OBS_TEXT_MULTILINE) 
	obs.obs_properties_add_text(props, "time_format", "time_format", obs.OBS_TEXT_DEFAULT)
	obs.obs_properties_add_text(props, "eve", "EVENT", obs.OBS_TEXT_DEFAULT)
	obs.obs_properties_add_text(props, "start", "START", obs.OBS_TEXT_DEFAULT)
	obs.obs_properties_add_text(props, "end", "END", obs.OBS_TEXT_DEFAULT)
	obs.obs_properties_add_int(props, "bar", "BAR LENGTH(100÷X)", 1, 10, 1)
	
	obs.obs_properties_add_button(props, "button", "Refresh", refresh_pressed)
	return props

def normalize_time(input_time_str):
	iso8601_time=parse_datetime(input_time_str)
	if iso8601_time is not None: # Check if iso8601_time is not None
		iso8601_time =iso8601_time.isoformat()
		return iso8601_time
	else:
		return "----" # Return an error message if parsing fails

def parse_datetime(datetime_str):
	for pattern in patterns:
		if re.match(pattern, datetime_str):
			try:
				if pattern == patterns[0]:
					return datetime.datetime.strptime(datetime_str, "%Y/%m/%d %H:%M")
				elif pattern == patterns[1]:
					return datetime.datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")
				elif pattern == patterns[2]:
					return datetime.datetime.strptime(datetime_str, "%Y-%m-%dT%H:%M:%S")
				elif pattern == patterns[3]:
					return datetime.datetime.strptime(datetime_str, "%Y/%m/%d")
				elif pattern == patterns[4]:
					return datetime.datetime.strptime(datetime_str, "%Y-%m-%d")
				elif pattern == patterns[5]:
					datetime_str=datetime_str.replace('Z', '+00:00')
					return datetime.datetime.fromisoformat(datetime_str) # Call fromisoformat directly on datetime
			except ValueError:
				pass
	return None

def script_update(settings):
	global interval
	global source_name
	global time_string
	global time_format
	global zone
	global st
	global en
	global obsbar
	global utc
	global UTC
	global JST
	global ibe
	
	ibe	=obs.obs_data_get_string(settings, "eve")
	utc_string	= obs.obs_data_get_string(settings, "utc")
	interval	= obs.obs_data_get_int(settings, "interval")
	source_name = obs.obs_data_get_string(settings, "source")
	time_string = obs.obs_data_get_string(settings, "format")
	time_format = obs.obs_data_get_string(settings, "time_format")
	zone = obs.obs_data_get_string(settings, "zone")
	st = obs.obs_data_get_string(settings, "start")
	en = obs.obs_data_get_string(settings, "end")
	st = normalize_time(str(st))
	en = normalize_time(str(en))
	obsbar = obs.obs_data_get_int(settings, "bar")
	# 正規表現パターン
	pattern = r"UTC(.)(\d{2}):(\d{2})"
	# 正規表現検索
	match = re.search(pattern, utc_string)
	utc=0
	utc_mstring=""
	if match:
		sign=match.group(1)
		hh = match.group(2)
		mm = match.group(3)
		utc=int(hh)+int(mm)/60
		if sign=="-":
			utc=-utc
		
	t_delta = datetime.timedelta(hours=9)  # 9時間
	JST = datetime.timezone(t_delta, 'JST') 
	t_delta = datetime.timedelta(hours=utc)
	UTC = datetime.timezone(t_delta, utc_string) 
	
	obs.timer_remove(update_text)
	
	if source_name != "":
		obs.timer_add(update_text, interval * 100)
