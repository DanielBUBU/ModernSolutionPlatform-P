import cv2
import numpy as np
import asyncio, multiprocessing, requests, time


def get_image_loop(address, frameQueue):
    getImageSession = requests.session()
    while True:
        response = getImageSession.get(
            f"http://{address}/cgi-bin/video.jpg", stream=True
        )
        arr = np.asarray(bytearray(response.content), dtype=np.uint8)
        frameQueue.put(cv2.imdecode(arr, -1))


def clear(frameQueue):
    frame = ""
    while not frameQueue.empty():
        frame = frameQueue.get()
    return frame


async def main():
    class pz6114camera:
        def __init__(self, address):
            self.address = address
            self.session = requests.session()
            self.getImageSession = requests.session()
            self.imageSavingPath = "image_capture_temp/"
            self.imageFileName = "image.jpg"
            self.frame = None
            self.lastCameraFrameTime = time.time()
            self.lastOpenCVFrameTime = time.time()
            self.cameraFPS = 0
            self.openCVFPS = 0

        def start(self):
            try:
                response = self.session.get(
                    f"http://{self.address}/cgi-bin/camctrl.cgi?move=home"
                )  # 鏡頭回正
                if response.status_code == 200:
                    response = self.getImageSession.get(
                        f"http://{self.address}/cgi-bin/video.jpg", stream=True
                    )  # 讓self.frame不為空
                    arr = np.asarray(bytearray(response.content), dtype=np.uint8)
                    self.frame = cv2.imdecode(arr, -1)
                    return True
                else:
                    return False
            except Exception as e:
                return e

        async def move(self, direction):
            if direction in ("up", "down", "left", "right", "home"):
                await asyncio.to_thread(
                    self.session.get,
                    f"http://{self.address}/cgi-bin/camctrl.cgi?move={direction}&speedtilt=-5&speedpan=-5",
                )
            else:
                raise Exception("invalid moving command")

        """async def save_image_loop(self):
            while True:
                response = await asyncio.to_thread(self.getImageSession.get , f'http://{PZ6114camera.address}/cgi-bin/video.jpg' , stream=True)
                if response.status_code == 200:
                    if not os.path.isdir(self.imageSavingPath):
                        os.mkdir(self.imageSavingPath)
                    async with self.lock: 
                        with open(self.imageSavingPath+self.imageFileName , 'wb') as saved_jpg:
                            await asyncio.to_thread(shutil.copyfileobj , response.raw , saved_jpg)"""

        def get_image(self):
            if time.time() - self.lastOpenCVFrameTime != 0:  # 有時候會這樣
                self.openCVFPS = 1 / (time.time() - self.lastOpenCVFrameTime)
            self.lastOpenCVFrameTime = time.time()
            return self.frame

    PZ6114camera = pz6114camera("192.168.0.100")
    cameraStatus = PZ6114camera.start()
    if cameraStatus == True:
        print("PZ6114 connected")
    elif cameraStatus == False:
        print("PZ6114 connection error")
        exit()
    elif type(cameraStatus) == "str":
        print("PZ6114 connection failed：" + cameraStatus)
        exit()

    async with asyncio.TaskGroup() as tg:  # 測試
        tg.create_task(PZ6114camera.move("up"))
        tg.create_task(PZ6114camera.move("down"))
        tg.create_task(PZ6114camera.move("left"))
        tg.create_task(PZ6114camera.move("right"))
        tg.create_task(PZ6114camera.move("home"))

    frameQueue = multiprocessing.Queue()
    for i in "12":
        multiprocessing.Process(
            target=get_image_loop, args=(PZ6114camera.address, frameQueue)
        ).start()

    range = 50
    updateFrame = 10
    frameNumber = 0

    tracker = cv2.TrackerCSRT_create()  # 創建追蹤器
    tracking = False  # 設定 False 表示尚未開始追蹤

    while True:
        keyName = cv2.waitKey(100)

        if frameNumber < updateFrame:
            frameNumber += 1
        else:
            async with asyncio.TaskGroup() as tg:
                frameNumber = 0
                if keyName == ord("w"):
                    tg.create_task(PZ6114camera.move("down"))

                if keyName == ord("a"):
                    tg.create_task(PZ6114camera.move("left"))

                if keyName == ord("s"):
                    tg.create_task(PZ6114camera.move("up"))

                if keyName == ord("d"):
                    tg.create_task(PZ6114camera.move("right"))

                if keyName == ord("h"):
                    tg.create_task(PZ6114camera.move("home"))

        # frame = cv2.resize(frame,(540,300))  # 縮小尺寸，加快速度

        if not frameQueue.empty():  # 有新幀
            PZ6114camera.frame = frameQueue.get()
            if frameQueue.qsize() > 5:
                PZ6114camera.frame = clear(frameQueue)
            PZ6114camera.cameraFPS = 1 / (
                time.time() - PZ6114camera.lastCameraFrameTime
            )
            PZ6114camera.lastCameraFrameTime = time.time()
            print(
                f"\nOpenCV FPS:{round(PZ6114camera.openCVFPS , 3)}\ncamera FPS:{round(PZ6114camera.cameraFPS , 3)}\nqueue size:{frameQueue.qsize()}"
            )
        frame = PZ6114camera.get_image()

        if keyName == ord("q"):
            break
        if keyName == ord("c"):
            tracking = False

        if keyName == ord("l"):
            area = cv2.selectROI(
                "oxxostudio", frame, showCrosshair=False, fromCenter=False
            )
            if area[0] != 0 | area[1] != 0 | area[2] != 0 | area[3] != 0:
                tracker.init(frame, area)  # 初始化追蹤器
                oldWidth = area[2]
                tracking = True  # 設定可以開始追蹤
            else:
                tracking = False
            # clear previous frames
        if tracking:
            success, point = tracker.update(frame)  # 追蹤成功後，不斷回傳左上和右下的座標
            if success:
                p1 = (int(point[0]), int(point[1]))
                # newWidth=point[2]
                centerP = (
                    int(point[0] + (point[2] / 2)),
                    int(point[1] + (point[3] / 2)),
                )
                bias = (
                    int(centerP[0] - (frame.shape[1] / 2)),
                    int((frame.shape[0] / 2) - centerP[1]),
                )
                p2 = (int(point[0] + point[2]), int(point[1] + point[3]))
                cv2.rectangle(frame, p1, p2, (0, 0, 255), 3)  # 根據座標，繪製四邊形，框住要追蹤的物件
                # print(bias)
                # print(bias[0])
                # TODO control cam using bias

                if frameNumber == 0:
                    async with asyncio.TaskGroup() as tg:
                        if bias[0] > range:
                            tg.create_task(PZ6114camera.move("right"))
                        else:
                            if bias[0] < -range:
                                tg.create_task(PZ6114camera.move("left"))
                        if bias[1] > range:
                            tg.create_task(PZ6114camera.move("up"))
                        else:
                            if bias[1] < -range:
                                tg.create_task(PZ6114camera.move("down"))

                # if newWidth>=oldWidth+2|newWidth<=oldWidth-2:
                #   tracker.init(frame, point)
                #  oldWidth=newWidth
            else:
                tracking = False
                print("update Fail")

        cv2.imshow("oxxostudio", frame)

    cv2.destroyAllWindows()


if __name__ == "__main__":
    asyncio.run(main())
