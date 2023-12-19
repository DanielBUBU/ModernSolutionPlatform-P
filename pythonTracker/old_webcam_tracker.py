import cv2
import platform , asyncio , time , psutil , json

async def main():
    
    class camera:
        def __init__(self):
            with open("settings.json", "r") as f:
                self.settings = json.load(f)
            self.availableResolution = ()

        def getAvailableResolution(self , cap):
            resolutions = []
            for res in self.settings['commonResolution']:
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, res[0])
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, res[1])
                rw = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
                rh = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
                if rw == res[0] and rh == res[1]:
                    resolutions.append(res)
            self.availableResolution = tuple(resolutions)
            print('available resolution：')
            for res in resolutions:
                print(f'{res[0]} X {res[1]}')                

    tracker = cv2.TrackerCSRT_create()  # 創建追蹤器
    tracking = False                    # 設定 False 表示尚未開始追蹤
    lastFrameTime = time.time()

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Cannot open camera")
        exit()

    webCam = camera()
    webCam.getAvailableResolution(cap)

    if platform.uname()[1] == 'DESKTOP-H6QBUE8':
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    else:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, webCam.availableResolution[-1][0])
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, webCam.availableResolution[-1][1])
    cap.set(cv2.CAP_PROP_FPS, 30)
    print(f'set resolution to {cap.get(cv2.CAP_PROP_FRAME_WIDTH)} X {cap.get(cv2.CAP_PROP_FRAME_HEIGHT)}\nset FPS to 30')

    """# 取得 Codec 名稱
    fourcc = cap.get(cv2.CAP_PROP_FOURCC)
    fourcc = int(fourcc)
    codec = ''.join([chr((fourcc >> 8 * i) & 0xFF) for i in range(4)])
    print("Codec: " + str(codec))"""

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Cannot receive frame")
            break

        print(f'FPS:{round(1 / (time.time() - lastFrameTime) , 1)}\ntotal CPU usage:{psutil.cpu_percent(percpu=False)}%')
        lastFrameTime = time.time()

        #frame = cv2.resize(frame,(540,300))  # 縮小尺寸，加快速度
        keyName = cv2.waitKey(1)

        if keyName == ord('q'):
            break
        if keyName == ord('c'):
            tracking = False
        if keyName == ord('a'):
            area = cv2.selectROI('oxxostudio', frame, showCrosshair=False, fromCenter=False)
            if area[0]!=0| area[1]!=0|area[2]!=0|area[3]!=0:
                tracker.init(frame, area)    # 初始化追蹤器
                oldWidth=area[2]
                tracking = True              # 設定可以開始追蹤
            else:
                tracking = False  
        if tracking:
            success, point = tracker.update(frame)   # 追蹤成功後，不斷回傳左上和右下的座標
            if success:
                p1 = (int(point[0]), int(point[1]))
                newWidth=point[2]
                centerP=(int(point[0] + (point[2]/2)), int(point[1] + (point[3]/2)))
                bias=(int(centerP[0]-(frame.shape[1]/2)), int((frame.shape[0]/2)-centerP[1]))
                p2 = (int(point[0] + point[2]), int(point[1] + point[3]))
                cv2.rectangle(frame, p1, p2, (0,0,255), 3)   # 根據座標，繪製四邊形，框住要追蹤的物件
                print(bias)
                #TODO control cam using bias
                if newWidth>=oldWidth+2|newWidth<=oldWidth-2:
                    tracker.init(frame, point)
                    oldWidth=newWidth
            else:
                tracking = False
                print("update Fail")

        cv2.imshow('oxxostudio', frame)

    cap.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    asyncio.run(main())