# -*- coding:utf-8 -*-
import requests
import json
import time
import sys
import random
import datetime
from urllib.parse import urlencode

try:
    import config_dev as config
except ImportError:
    import config

headers = {
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
    'Host': 'app.buaa.edu.cn',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-origin',
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/80.0.3987.87 Chrome/80.0.3987.87 Safari/537.36',
    'X-Requested-With': 'XMLHttpRequest',
}

checkinPlayload = {
    'sfzx' : '1', # 是否在校
    'tw' : '1', # 体温
    'area' : '北京市 海淀区',
    'city' : '北京市',
    'province' : '北京市',
    'address' : '北京市海淀区花园路街道北京航空航天大学学生公寓13号楼北京航空航天大学学院路校区',
    'geo_api_info' : '{\"type\":\"complete\",\"info\":\"SUCCESS\",\"status\":1,\"XDa\":\"jsonp_229421_\",\"position\":{\"Q\":39.98488,\"R\":116.34623999999997,\"lng\":116.34624,\"lat\":39.98488},\"message\":\"Get ipLocation success.Get address success.\",\"location_type\":\"ip\",\"accuracy\":null,\"isConverted\":true,\"addressComponent\":{\"citycode\":\"010\",\"adcode\":\"110108\",\"businessAreas\":[{\"name\":\"五道口\",\"id\":\"110108\",\"location\":{\"Q\":39.99118,\"R\":116.34157800000003,\"lng\":116.341578,\"lat\":39.99118}}],\"neighborhoodType\":\"生活服务;生活服务场所;生活服务场所\",\"neighborhood\":\"北京航空航天大学\",\"building\":\"北京航空航天大学学生公寓13号楼\",\"buildingType\":\"商务住宅;住宅区;宿舍\",\"street\":\"北四环中路\",\"streetNumber\":\"248楼\",\"country\":\"中国\",\"province\":\"北京市\",\"city\":\"\",\"district\":\"海淀区\",\"township\":\"花园路街道\"},\"formattedAddress\":\"北京市海淀区花园路街道北京航空航天大学学生公寓13号楼北京航空航天大学学院路校区\",\"roads\":[],\"crosses\":[],\"pois\":[]}',
    'sfcyglq' : '0', # 是否处于隔离期
    'sfyzz' : '0', # 是否有症状
    'qtqk' : '', # 其他情况
    'askforleave' : '0' # 请假
}

# 检查当前是否是该打卡的时间
def checkMorning():
    # 早7-9
    moringBegin = datetime.time(7,0,0)
    moringEnd = datetime.time(9,0,0)
    now = datetime.datetime.now().time()
    return moringBegin <= now <= moringEnd

def checkNoon():
    # 午11-13
    noonBegin = datetime.time(11,0,0)
    noonEnd = datetime.time(13,0,0)
    now = datetime.datetime.now().time()
    return noonBegin <= now <= noonEnd

def checkNight():
    # 晚18-20
    nightBegin = datetime.time(18,0,0)
    nightEnd = datetime.time(20,0,0)
    now = datetime.datetime.now().time()
    return nightBegin <= now <= nightEnd


def sendSC(text, desp, key):
    if len(config.SCKey) == 0:
        return
    SCUrl = 'https://sc.ftqq.com/' + key + '.send?'
    params = {'text': text, 'desp': desp}
    requests.get(SCUrl + urlencode(params))


def checkin():
    # login, fetch cookies
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
    print('Logging in......')
    rep = requests.post(
        'https://app.buaa.edu.cn/uc/wap/login/check',
        data={
            'username': config.username,
            'password': config.password
        },
        headers=headers,
        timeout=10
    )
    if json.loads(rep.content.decode())['e'] != 0:
        raise Exception(rep.content.decode())
    else:
        print('Login success.')
    cookies = rep.cookies.get_dict()

    # fetch basic info
    print('Fetching basic info......')
    infoPage = requests.get(
        'https://app.buaa.edu.cn/site/ncov/xisudailyup',
        cookies=cookies,
        headers=headers,
        timeout=10
    )

    time2sleep = random.randint(5,30)
    print('Sleep for %d seconds......' % time2sleep)
    time.sleep(time2sleep)

    # do check in
    print('Checking in......')
    rep = requests.post(
        'https://app.buaa.edu.cn/xisuncov/wap/open-report/save',
        data=checkinPlayload,
        headers=headers,
        cookies=cookies
    )
    respStr = rep.content.decode()
    if rep.status_code == 200:
        respDict = eval(respStr)
        print(rep, rep.content.decode(), '\nDone.')
        if "e" in respDict:
            if respDict["e"] == 0:
                sendSC('打卡成功！', respDict["m"], config.SCKey)
            elif respDict["m"] == '您已上报过':
                sendSC('重复打卡！', respDict["m"], config.SCKey)
            else:
                raise Exception(respDict["m"])
    else:
        raise Exception(respStr)

def tryCheckin():
    for i in range(5):
        try:
            checkin()
            return True
        except Exception as err:
            print(err)
            sendSC('打卡失败！', err, config.SCKey)
            time.sleep(60) # 60s后重试
    return False

def main():
    date = datetime.datetime.now().date()
    morningDone = False
    noonDone = False
    nightDone = False
    while True:
        nowDate = datetime.datetime.now().date()
        if nowDate > date:
            # 新的一天
            date = nowDate
            morningDone = False
            noonDone = False
            nightDone = False
        
        # 到打卡时间了
        if not morningDone and checkMorning():
            print('早晨打卡啦~')
            morningDone = tryCheckin()
        if not noonDone and checkNoon():
            print('中午打卡啦~')
            noonDone = tryCheckin()
        if not nightDone and checkNight():
            print('晚上打卡啦~')
            nightDone = tryCheckin()
        
        # 随机休眠5-30分钟
        sleepTime = random.randint(5, 30)
        print('休眠%d分钟后重试' % sleepTime)
        time.sleep(sleepTime * 60)

if __name__ == '__main__':
    main()
    
