#!/usr/bin/python
# -*- coding: utf-8 -*-
import RPi.GPIO as GPIO
from grovepi import *
from grove_rgb_lcd import *
from time import sleep
from math import isnan
from datetime import datetime
import datetime
import requests
import urllib
import json
import time
import math
import grovepi
import sys
import operator
import threading
import random
import pytz
import pygame
from urllib2 import Request, urlopen

from flask import Flask, flash, redirect, render_template, request, session, abort, url_for
import os

# Connections GPIO
Switch1 = 23              # 버튼 1
Switch2 = 24              # 버튼 2

GPIO.setmode(GPIO.BCM)
GPIO.setup(Switch1, GPIO.IN)# if GPIO.input(Switch) == True: ... 이런식으로 작성하면됨.
GPIO.setup(Switch2, GPIO.IN)      

# Connections Grove PI+
buzzer_pin = 2          # 부저 D2
potentiometer = 2       # Analog port A2
dht_sensor_port = 7     # 온습도 센서 D7
dht_sensor_type = 0     # use 0 for the blue-colored sensor and 1 for the white-colored sensor

pinMode(buzzer_pin,"OUTPUT")   # Assign mode for buzzer as output
# pinMode(button,"INPUT")      # Assign mode for Button as input


################################################
################################################ 새로운 코드
################################################

dic_alarm_data = {}
dic_alarm_data['191219_2014'] = (2019, 12, 19, 20, 14)#년, 월, 일, 시, 분
dic_alarm_data['191222_1010'] = (2019, 12, 22, 10, 10)#년, 월, 일, 시, 분
dic_alarm_data['191225_1112'] = (2019, 12, 25, 11, 12)#년, 월, 일, 시, 분
dic_alarm_data['200605_0605'] = (2020, 6, 5, 6, 5)#년, 월, 일, 시, 분
dic_alarm_data['200112_1234'] = (2020, 1, 12, 12, 34)#년, 월, 일, 시, 분
dic_alarm_data['201225_0512'] = (2020, 12, 25, 5, 12)#년, 월, 일, 시, 분
dic_alarm_data['200402_0402'] = (2020, 4, 2, 4, 2)#년, 월, 일, 시, 분
#삭제할땐 del 1912..

setText_norefresh("                       \n                        ") # LCD텍스트 삭제

# 전역변수 생성
setdata = 0
setyear = 0
setmonth = 0
setday = 0
sethour = 0
setmin = 0
    
def sendText(accessToken) : # 네이버 라인 코드
    url = 'https://notify-api.line.me/api/notify'
    payload = 'message="' + u"아들이 일어나지 않습니다.".encode("utf-8")
    headers = {
        'Content-Type' : "application/x-www-form-urlencoded",
        'Cache-Control' : "no-cache",
        'Authorization' : "Bearer " + accessToken,
    }
    reponse = requests.request("POST",url,data=payload, headers=headers)
    responseJson = json.loads(((reponse.text).encode('utf-8')))
    return responseJson

def get_api_date() :
    time_now = datetime.datetime.now(tz=pytz.timezone('Asia/Seoul')).strftime('%H')
    check_time = int(time_now)
    
    if(int(datetime.datetime.now(tz=pytz.timezone('Asia/Seoul')).strftime('%M'))<40):
        check_time = check_time-1
        
    date_now = datetime.datetime.now(tz=pytz.timezone('Asia/Seoul')).strftime('%Y%m%d')
    check_date = int(date_now)
    
    if(check_time < 10):
        check_time_str = str(0) + str(check_time) + '00'
    else:
        check_time_str = str(check_time) + '00'
        
    return (str(check_date), check_time_str)
   
def get_weather_data() :
    api_date, api_time = get_api_date()
    url = "http://newsky2.kma.go.kr/service/SecndSrtpdFrcstInfoService2/ForecastTimeData?"
    auth = "PrJGM6XhqxTfA3FJJG2NnjG32ZwfSTbFDyLAMugQGegX9ZkJCn0tA%2BOtFmfZc%2FWH3ECvWWIjGSfz1KSvzg7fCw%3D%3D"
    key = "serviceKey=" + auth
    date = "&base_date=" + api_date
    time = "&base_time=" + api_time
    nx = "&nx=86"
    ny = "&ny=96"
    numOfRows = "&numOfRows=100"
    code = "&_type=json"
    api_url = url + key + date + time + nx + ny + numOfRows + code

    print("날씨 불러오는중..")
    print(api_url)

    request = Request(api_url)
    request.get_method = lambda: 'GET'
    
    data = urlopen(request).read()
    data_json = json.loads(data)
   
    parsed_json = data_json['response']['body']['items']['item']
    target_date = parsed_json[0]['fcstDate']  # get date and time
    target_time = parsed_json[0]['fcstTime']
        
    passing_data = {}
    count = 0
    T1Hresult = 1.0 #온도
    REHresult = 1.0 #습도
    PTYresult = 0 #강수형태
    for one_parsed in parsed_json:
        if one_parsed['fcstDate'] == target_date and one_parsed['fcstTime'] == target_time: #get today's data
            passing_data[one_parsed['category']] = one_parsed['fcstValue']
            if(count==4):#온도 추출
                T1Hresult = one_parsed['fcstValue']
            if(count==5):#습도 추출
                REHresult = one_parsed['fcstValue']
            if(count==1):#강수 형태
                PTYresult = one_parsed['fcstValue']
            count = count + 1
            
    return (str(target_time), T1Hresult, REHresult, PTYresult)#측정 시간, 온도, 습도, 강수형태

def NextAlarm() :
    try:
        data2 = sorted(dic_alarm_data.items(), key=operator.itemgetter(0))# 191212_2012 이 문자열로 소팅
        global setdata, setyear, setmonth, setday, sethour, setmin
        setdata = data2[0][0]
        setyear = data2[0][1][0]
        setmonth = data2[0][1][1]
        setday = data2[0][1][2]
        sethour = data2[0][1][3]
        setmin = data2[0][1][4]
        # print(setyear,setmonth,setday,sethour,setmin)
        return False
    except IndexError:
        print("다음 알람이 없음. 인덱싱 할 수 없습니다.")
        return True
    
alarm_empty = False
TextMode = 1 # LCD 페이지
MenuSel = 0 # 메뉴선택
AlarmSel  = 0 # 알람선택
weatherstring = '0'
temper = 0
hum = 0

def background_thread(): # 알람시계 내부코드
    global alarm_empty, TextMode, MenuSel, AlarmSel, setyear, weatherstring, temper, hum
    localtime = datetime.datetime.now() # 현재 시각저장
    NextAlarm() # 다음 알람을 전역변수에 저장.
    [ temper,hum ] = dht(dht_sensor_port,dht_sensor_type)
    LCDBackLightTime = localtime + datetime.timedelta(seconds=5) # 5초 동안 백라이트 켜짐.
    refresh_api = datetime.datetime.now() # 1시간마다 날씨측정
    while True : # 1초마다 작동.. while문은 절대 꺼지면 안됨.
        localtime = datetime.datetime.now() # 현재 시각저장
        settime = datetime.datetime(setyear,setmonth,setday,sethour,setmin)
        settime2 = settime + datetime.timedelta(minutes=60) # 울린지 3분이 넘었다면 자동으로 메세지 전송   
        digitalWrite(buzzer_pin,0) # 부저는 일단 조용히
            
        ##########################  스위치 1, 2
        ##########################

        if (localtime<LCDBackLightTime): # 백라이트 타이머
            setRGB(255,255,255) # 하얀색 LCD
        else:
            setRGB(0,0,0) # 꺼짐.
        
        if (localtime>refresh_api): # 날씨 측정
            setRGB(125,125,125) # 하얀색 LCD
            setText_norefresh("get weather data\n now loading..  ")
            target_time, T1Hresult, REHresult, PTYresult = get_weather_data()
            if(PTYresult==0):
                ptystring = "Sunny"
            elif(PTYresult==1):
                ptystring = "Rain"
            elif(PTYresult==3):
                ptystring = "Snow"
            else:
                ptystring = "error"

            weatherstring = u'기준시각 : ' + str(int(target_time)/100) + u'시 / 온도 : ' + str(T1Hresult) + u'°C / 습도 : ' + str(REHresult) + u'% / ' + ptystring
            print(target_time, T1Hresult, REHresult, PTYresult)
            refresh_api = datetime.datetime.now() + datetime.timedelta(minutes=60) # 1시간마다 날씨측정

        if (GPIO.input(Switch1) == True) : # 스위치1 누를때마다 시간/온습도 변환, 뒤로가기
            LCDBackLightTime = localtime + datetime.timedelta(seconds=5) # 5초 동안 백라이트 켜짐.
            if(TextMode == 1) : # 시계모드
                setText_norefresh("                       \n                        ")
                TextMode = 2
            elif(TextMode == 2) : # 다음 알람시간은?
                setText_norefresh("                       \n                        ")
                TextMode = 3
            elif(TextMode == 3) : # 실내기온모드
                setText_norefresh("                       \n                        ")
                TextMode = 4
            elif(TextMode == 4) : # 실외기온모드
                setText_norefresh("                       \n                        ")
                TextMode = 1
            elif(TextMode == 10) : # 메뉴 진입중일시 시계모드로 돌아오기.
                setText_norefresh("                       \n                        ")
                TextMode = 1
            elif(TextMode >= 11 and TextMode <= 15 or TextMode == 21): # 메뉴 세부내용 진입 중 누르면 메뉴로 돌아오기.
                TextMode = 10
            elif(TextMode == 22):
                TextMode = 21
            sleep(0.1)
                
        if (GPIO.input(Switch2) == True): # 스위치2 누르면 메뉴로 진입.
            LCDBackLightTime = localtime + datetime.timedelta(minutes=1) # 1분 동안 백라이트 켜짐.
            if(1 <= TextMode <= 4):
                TextMode = 10
            elif(TextMode == 10 and MenuSel == 1): # 알람 추가 진입 /// 년, 월, 일, 시, 분 순으로
                TextMode = 11 # 년
            elif(TextMode == 11):
                TextMode = 12 # 월
            elif(TextMode == 12):
                TextMode = 13 # 일
            elif(TextMode == 13):
                TextMode = 14 # 시
            elif(TextMode == 14):
                TextMode = 15 # 분
            elif(TextMode == 15): # 알람저장!!
                tempmonth2 = tempmonth
                tempday2 = tempday
                temphour2 = temphour
                tempmin2 = tempmin
                if(tempmonth<10):
                    tempmonth2 = str(0)+str(tempmonth)
                if(tempday<10):
                    tempday2 = str(0)+str(tempday)
                if(temphour<10):
                    temphour2 = str(0)+str(temphour)
                if(tempmin<10):
                    tempmin2 = str(0)+str(tempmin)
                
                dic_alarm_data[str(tempyear)+str(tempmonth2)+str(tempday2)+'_'+str(temphour2)+str(tempmin2)] = (tempyear+2000, tempmonth, tempday, temphour, tempmin)#년, 월, 일, 시, 분
                
                print '알람추가 완료 : ',
                print(datetime.datetime(tempyear+2000,tempmonth,tempday,temphour,tempmin))
                alarm_empty = NextAlarm() # 알람 재정렬
                TextMode = 10
            elif(TextMode == 10 and MenuSel == 2): # 알람 확인 및 삭제 진입
                TextMode = 21
            elif(TextMode == 21 and len(dic_alarm_data) != 0): # 삭제하시겠습니까?
                TextMode = 22
            elif(TextMode == 22):
                TextMode = 23 # 삭제완료..
            sleep(0.1)
                
            
        ##########################  LCD에 표시될 내용
        ##########################
        
        if(TextMode == 1) : # 시계모드
            setText_norefresh("Date : " + localtime.strftime("%y/%m/%d") + " \nTime : " + localtime.strftime("%H:%M:%S") +" ")
        elif(TextMode == 2) : # 다음 알람시간은?
            if(alarm_empty == True): # 아무것도 없다면
                setText_norefresh("Next Alarm      \n :Alarm is empty")
            else:
                setText_norefresh("Next Alarm :  \n " + settime.strftime("%y/%m/%d %H:%M"))
        elif(TextMode == 3) : # 현재 기온모드
            [ temper,hum ] = dht(dht_sensor_port,dht_sensor_type)
            setText_norefresh("Temp:" + str(temper) + "C\n" + "Humidity :" + str(hum) + "%")
        elif(TextMode == 4) : # 실외기온모드
            if(PTYresult==0):
                ptystring = "Sunny"
            elif(PTYresult==1):
                ptystring = "Rain"
            elif(PTYresult==3):
                ptystring = "Snow"
            else:
                ptystring = "error"
            setText_norefresh("Out Temp:" +  str(T1Hresult) + "C  \n" + str(REHresult) + "%  .." + ptystring)
        elif(TextMode == 10) : # 메뉴 진입 1 (알람 추가) 2 (알람 확인 및 삭제)
            i = grovepi.analogRead(potentiometer)
            i = i * 2 / 1024 # 2등분 (0,1)
            if(i==0) :
                MenuSel = 1
                setText_norefresh("Menu            \n 1. Alarm add   ")
            elif(i==1) :
                MenuSel = 2
                setText_norefresh("Menu            \n 2. Alarm del   ")
                
        if(TextMode == 11) : # 1. 알람 추가 진입 /// 년
            i = grovepi.analogRead(potentiometer)
            i = i * 32 / 1024 + 19# 2019~2050
            tempyear = i
            setText_norefresh("Alarm add      \n year : " + str(i+2000))
        elif(TextMode == 12) : # 1. 알람 추가 진입 /// 월
            i = grovepi.analogRead(potentiometer)
            i = i * 12 / 1024 + 1# 1~12                
            tempmonth = i
            setText_norefresh("Alarm add      \n month : " + str(i))
        elif(TextMode == 13) : # 1. 알람 추가 진입 /// 일
            i = grovepi.analogRead(potentiometer)
            if(tempmonth == 1,3,5,7,8,10,12):
                i = i * 31 / 1024 + 1# 1~31
            elif(tempmonth == 2):
                i = i * 28 / 1024 + 1# 1~28
            else:
                i = i * 30 / 1024 + 1# 1~30
            tempday = i
            setText_norefresh("Alarm add      \n day : " + str(i))
        elif(TextMode == 14) : # 1. 알람 추가 진입 /// 시
            i = grovepi.analogRead(potentiometer)
            i = i * 24 / 1024 # 0~23
            temphour = i
            setText_norefresh("Alarm add      \n hour : " + str(i))
        elif(TextMode == 15) : # 1. 알람 추가 진입 /// 분
            i = grovepi.analogRead(potentiometer)
            i = i * 60 / 1024 # 0~59
            tempmin = i
            setText_norefresh("Alarm add      \n minute : " + str(i))
        elif(TextMode == 21) : # 2. 알람 확인 및 삭제 진입
            i = grovepi.analogRead(potentiometer)
            data2 = sorted(dic_alarm_data.items(), key=operator.itemgetter(0)) # 데이터 재정렬
            i = i * (len(data2)+1) / 1024 # data2의 개수+1만큼 나눠짐
            AlarmSel = i # 지울 알람을 선택
            print(data2)
            if(len(data2) == 0): # 있는게 없다? len이 0일때..
                setText_norefresh("Alarm List      \n Alarm is empty ")
            elif(i == len(data2)): # 마지막줄이라면 
                setText_norefresh(">" + str(i) + ". " + data2[i-1][0] + " \n Last Alarm..   ")
            else: # 
                if(i == 0): # 첫번째 줄은 설명
                    setText_norefresh("Alarm List      \n>" + str(i+1) + ". " + data2[i][0])
                else:
                    setText_norefresh(" " + str(i) + ". " + data2[i-1][0] + " \n>" + str(i+1) + ". " + data2[i][0])
        elif(TextMode == 22): # 2. 이 알람을 진짜로 삭제하시겠습니까?
            if(AlarmSel>=len(data2)):
                AlarmSel = AlarmSel-1
            setText_norefresh("Delete Alarm?   \n " + str(AlarmSel+1) + ". " + data2[AlarmSel][0])
        elif(TextMode == 23): # 2. 삭제완료..
            del dic_alarm_data[data2[AlarmSel][0]]
            setText_norefresh("Delete          \n Complete       ")
            TextMode = 21
            alarm_empty = NextAlarm() # 알람 재정렬
            sleep(1)
        
        ##########################  알람시각이 오면
        ##########################

        if (localtime>=settime and alarm_empty == False) : # 알람시각이 오고, 알람이 있으면
            print '알람시작 : ',
            print(settime)
            pygame.init()
            pygame.mixer.music.load("good_morning.wav")
            pygame.mixer.music.play(-1)
            del dic_alarm_data[setdata] # 이 알람은 삭제.
            setText_norefresh("                       \n                        ") # LCD텍스트 삭제
            while True : # 끌때까지 울리자.
                setText_norefresh("Time : " + localtime.strftime("%H:%M:%S") + " \n Wake Up!!      ")
                localtime = datetime.datetime.now()
                if(localtime.second % 2 == 1): # 반짝반짝 백라이트
                    setRGB(0,255,0) # 초록색 LCD
                else:
                    setRGB(0,0,255) # 파란색 LCD
                    
                if (GPIO.input(Switch1) == True or GPIO.input(Switch2) == True) : # 스위치1 또는 스위치2 누르면 문제가 나옴.
                    limittime = datetime.datetime.now() + datetime.timedelta(seconds=60) # 지금부터 60초 준다
                    #문제 출시 50~90 x 2~3 + 1~9 = ?
                    a = random.randrange(50,91)
                    b = random.randrange(2,4)
                    c = random.randrange(1,10)
                    answer = a*b+c
                    right_answer = False
                    sleep(0.1)
                    while True : 
                        setRGB(255,255,255)
                        localtime = datetime.datetime.now()
                        digitalWrite(buzzer_pin,0) # 삒소리 잠시 멈춰줄께 하지만 60초 뒤에 다시 울릴꺼야 그전에 풀어라
                        timer = (limittime - localtime).seconds # 타이머
                        i = grovepi.analogRead(potentiometer)
                        i = i * 200 / 1024 + 100
                        setText_norefresh("limit time = " + str(timer) + " \n" + str(a) + " x " + str(b) + " + " + str(c) + " = " + str(i) + "   ")
                        myanswer = i # 나의 정답은??
                        if (GPIO.input(Switch2) == True) : # 스위치1 누를 때 정답 확인
                            if(myanswer==answer) : # 정답이 맞다면
                                right_answer = True
                                break;
                            else: # 아니라면
                                setText_norefresh("wrong Answer!")
                                setRGB(255,0,0)
                                digitalWrite(buzzer_pin,1) # 잠시 삒!
                                sleep(0.2)
                        if(localtime >= limittime) : # 60초가 지났어?
                            break;
                        sleep(0.1) 
                    if(right_answer==True):
                        break
                else:
                    digitalWrite(buzzer_pin,1)
                    if (localtime >= settime2) : # 울린지 ?분이 지나면 메세지 전송
                        setText_norefresh("Time Over       \n Sending Message..           ") # LCD텍스트 삭제
                        digitalWrite(buzzer_pin,0)               
                        print (sendText('OdytsUCcRF1TOTOTKM4DcZyyPX8q0tl21zWyDXOnunD')) # 라인 ACCESS TOKEN
                        break;
                sleep(0.01)
            pygame.mixer.music.stop()
            alarm_empty = NextAlarm()
            print("알람완료..")

            if(alarm_empty == True):
                setyear = 9999

            localtime = datetime.datetime.now() # 현재 시각저장
            settime = datetime.datetime(setyear,setmonth,setday,sethour,setmin)

            print '현재시각 : ',
            print(localtime)
            print '다음알람 : ',
            print(settime)
            
            print("")
            
            setText_norefresh("                       \n                        ")
            LCDBackLightTime = localtime + datetime.timedelta(seconds=5)
            TextMode = 3 # 현재 기온모드로 변경
            
    sleep(0.2) # 0.1초마다 시간갱신
            
thread = None

if thread is None: # 내부코드 시작.
    thread = threading.Thread(target=background_thread)
    thread.start()

################################################
################################################ 이하 서버코드
################################################

app = Flask(__name__)

@app.route("/", methods=['GET']) #route 데코레이터 - 어떤 URL이 펑션을 호출할지 알려준다.
@app.route("/main", methods=['GET'])#두가지 URL 전부 main.html로 간다.
def main():
    if not session.get('logged_in'):#로그인 되어 있지 않으면 로그인 페이지로 이동
        return render_template('login.html')
    else:
        data2 = sorted(dic_alarm_data.items(), key=operator.itemgetter(0))# 191212_2012 이 문자열로 소팅
        my_list = []
        for i in range(len(data2)):
            temp = str(i+1) + u'. ' + str(data2[i][1][0])+u'년 '+str(data2[i][1][1])+u'월 '+str(data2[i][1][2])+u'일 '+str(data2[i][1][3])+u'시 '+str(data2[i][1][4])+u'분'
            my_list.append(temp) # 배열에 추가
        if(len(data2)==0) : # 없으면
            my_list = [u'예정된 알람이 없습니다.']
        intemperhum = u'온도 : ' + str(temper) + u'°C / 습도 : ' + str(hum) + u'%'
        return render_template('main.html', my_list=my_list, weatherstring=weatherstring, intemperhum=intemperhum)

@app.route("/login", methods=['POST'])#로그인으로 이동.
def do_admin_login():
    #폼에서 넘어온 데이터를 가져와 정해진 유저네임과 암호를 비교하고 참이면 세션을 저장한다.
    #회원정보를 DB구축해서 추출하서 비교하는 방법으로 구현 가능 - 여기서는 바로 적어 줌
    if request.form['password'] == 'password' and request.form['username'] == 'admin':
        session['logged_in'] = True #세선 해제는 어떻게?
    else:
        flash('유저네임이나 암호가 맞지 않습니다.')
    return main()

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('main'))
   
@app.route("/addalarm")
def addalarm():
    return render_template('addalarm.html')

@app.route("/addalarm_result", methods=['POST', 'GET'])
def addalarm_result():
    global alarm_empty
    if request.method == 'POST':
        result = request.form
        date_string = result['userdate']
        time_string = result['usertime']
        
        tempyear = int(date_string[2:4])
        tempmonth = int(date_string[5:7])
        tempday = int(date_string[8:10])
        temphour = int(time_string[0:2])
        tempmin = int(time_string[3:5])

        tempmonth2 = tempmonth
        tempday2 = tempday
        temphour2 = temphour
        tempmin2 = tempmin
        if(tempmonth<10):
            tempmonth2 = str(0)+str(tempmonth)
        if(tempday<10):
            tempday2 = str(0)+str(tempday)
        if(temphour<10):
            temphour2 = str(0)+str(temphour)
        if(tempmin<10):
            tempmin2 = str(0)+str(tempmin)
        
        dic_alarm_data[str(tempyear)+str(tempmonth2)+str(tempday2)+'_'+str(temphour2)+str(tempmin2)] = (tempyear+2000, tempmonth, tempday, temphour, tempmin)#년, 월, 일, 시, 분
        
        print '알람추가 완료 : ',
        print(datetime.datetime(tempyear+2000,tempmonth,tempday,temphour,tempmin))
        alarm_empty = NextAlarm() # 알람 재정렬
        
        return redirect(url_for('main'))

@app.route("/delalarm")
def delalarm():
    data2 = sorted(dic_alarm_data.items(), key=operator.itemgetter(0))# 191212_2012 이 문자열로 소팅
    my_list = []
    for i in range(len(data2)):
        temp = str(i+1) + u'. ' + str(data2[i][1][0])+u'년 '+str(data2[i][1][1])+u'월 '+str(data2[i][1][2])+u'일 '+str(data2[i][1][3])+u'시 '+str(data2[i][1][4])+u'분'
        print(temp)
        my_list.append(temp) # 배열에 추가
    return render_template('delalarm.html', my_list=my_list)

@app.route("/delalarm_result", methods=['POST', 'GET'])
def delalarm_result():
    global alarm_empty
    if request.method == 'POST':
        result = request.form
        data2 = sorted(dic_alarm_data.items(), key=operator.itemgetter(0))# 191212_2012 이 문자열로 소팅
        del dic_alarm_data[data2[int(result['text'])-1][0]]
        alarm_empty = NextAlarm() # 알람 재정렬
        return redirect(url_for('main'))

if __name__ == '__main__':
    app.secret_key = os.urandom(12) #좀 더 알아 볼것. 시크릿키는 세션등의 기능을 위해 반드시 필요하다.
    app.run(host='0.0.0.0') #앱 시작.