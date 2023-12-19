import asyncio , multiprocessing , cv2 , json , psutil , time , io
import mediapipe
from fastapi import FastAPI
from fastapi.responses import HTMLResponse , StreamingResponse
from pygrabber.dshow_graph import FilterGraph

COMMON_RESOLUTION = ((16, 16), (42, 11), (32, 32), (40, 30), (42, 32), (48, 32), (80, 25), (60, 40), (72, 40), (84, 48), (64, 64), (170, 25), (72, 64), (128, 36), (75, 64), (150, 40), (96, 64), (96, 64), (128, 48), (96, 65), (102, 64), (108, 70), (101, 80), (128, 64), (96, 96), (128, 96), (240, 64), (160, 100), (160, 102), (128, 128), (128, 160), (160, 120), (160, 144), (144, 168), (160, 152), (160, 160), (140, 192), (160, 200), (320, 100), (224, 144), (208, 176), (240, 160), (220, 176), (160, 256), (180, 248), (208, 208), (256, 192), (280, 192), (256, 212), (432, 128), (256, 224), (240, 240), (256, 240), (320, 192), (320, 192), (320, 200), (256, 256), (256, 256), (320, 208), (320, 224), (320, 240), (320, 256), (320, 256), (384, 224), (368, 240), (372, 240), (376, 240), (272, 340), (400, 240), (512, 192), (448, 224), (320, 320), (432, 240), (560, 192), (400, 270), (512, 212), (384, 288), (480, 234), (400, 300), (480, 250), (312, 390), (512, 240), (320, 400), (640, 200), (480, 272), (512, 256), (512, 256), (416, 352), (480, 320), (640, 240), (640, 240), (640, 256), (512, 342), (368, 480), (496, 384), (800, 240), (512, 384), (640, 320), (640, 350), (640, 360), (480, 500), (512, 480), (720, 348), (720, 350), (640, 400), (720, 364), (800, 352), (600, 480), (640, 480), (640, 500), (640, 512), (768, 480), (800, 480), (848, 480), (854, 480), (800, 600), (960, 540), (832, 624), (960, 544), (1024, 576), (960, 640), (1024, 600), (1024, 640), (960, 720), (1136, 640), (1138, 640), (1024, 768), (1024, 800), (1152, 720), (1152, 768), (1280, 720), (1120, 832), (1280, 768), (1152, 864), (1334, 750), (1280, 800), (1152, 900), (1024, 1024), (1366, 768), (1280, 854), (1280, 960), (1600, 768), (1080, 1200), (1440, 900), (1440, 900), (1280, 1024), (1440, 960), (1600, 900), (1400, 1050), (1440, 1024), (1440, 1080), (1600, 1024), (1680, 1050), (1776, 1000), (1600, 1200), (1600, 1280), (1920, 1080), (1440, 1440), (2048, 1080), (1920, 1200), (2048, 1152), (1792, 1344), (1920, 1280), (2280, 1080), (2340, 1080), (1856, 1392), (2400, 1080), (1800, 1440), (2880, 900), (2160, 1200), (2048, 1280), (1920, 1400), (2520, 1080), (2436, 1125), (2538, 1080), (1920, 1440), (2560, 1080), (2160, 1440), (2048, 1536), (2304, 1440), (2256, 1504), (2560, 1440), (2576, 1450), (2304, 1728), (2560, 1600), (2880, 1440), (2960, 1440), (2560, 1700), (2560, 1800), (2880, 1620), (2560, 1920), (3440, 1440), (2736, 1824), (2880, 1800), (2880, 1920), (2560, 2048), (2732, 2048), (3200, 1800), (2800, 2100), (3072, 1920), (3000, 2000), (3840, 1600), (3200, 2048), (3240, 2160), (5120, 1440), (3200, 2400), (3840, 2160), (4096, 2160), (3840, 2400), (4096, 2304), (5120, 2160), (4480, 2520), (4096, 3072), (4500, 3000), (5120, 2880), (5120, 3200), (5120, 4096), (6016, 3384), (6400, 4096), (6000, 4500), (6400, 4800), (6480, 3240), (7680, 4320), (7680, 4800), (8192, 4320), (8192, 4608), (10240, 4320), (8192, 8192), (15360, 8640), (16384, 8640))

def get_camera_frame_func(Resolution , selectedCameraIndex , cameraFrameQueue , cameraFPSQueue , cam2faceQueue):
    cap = cv2.VideoCapture(selectedCameraIndex)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, Resolution[0])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, Resolution[1])
    #cap.set(cv2.CAP_PROP_FPS, 30)
    frameTimeList = []
    while True:
        ret, img = cap.read()
        if not ret:
            continue
        if cameraFrameQueue.full():
            try:
                cameraFrameQueue.get_nowait()
            except:
                pass
        try:
            cameraFrameQueue.put_nowait(img)
        except:
            pass
        frameTimeList.append(time.time())
        while time.time() - frameTimeList[0] > 1:
            del frameTimeList[0]
        if cameraFPSQueue.full():
            try:
                cameraFPSQueue.get_nowait()
            except:
                pass
        try:
            cameraFPSQueue.put_nowait(len(frameTimeList))
        except:
            pass
        if cam2faceQueue.full():
            try:
                cam2faceQueue.get_nowait()
            except:
                pass
        try:
            cam2faceQueue.put_nowait(img)
        except:
            pass

def get_face_detection_frame_func(cam2faceQueue , faceDetectFrameQueue , faceDetectFPSQueue):
    frameTimeList = []
    mp_face_detection = mediapipe.solutions.face_detection
    mp_drawing = mediapipe.solutions.drawing_utils
    with mp_face_detection.FaceDetection(model_selection=0, min_detection_confidence=0.5) as face_detection:
        while True:
            img = cam2faceQueue.get()
            img.flags.writeable = False
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            results = face_detection.process(img)
            img.flags.writeable = True
            #img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            if results.detections:
                for detection in results.detections:
                    mp_drawing.draw_detection(img, detection)
            if faceDetectFrameQueue.full():
                try:
                    faceDetectFrameQueue.get_nowait()
                except:
                    pass
            try:
                faceDetectFrameQueue.put_nowait(img)
            except:
                pass
            frameTimeList.append(time.time())
            while time.time() - frameTimeList[0] > 1:
                del frameTimeList[0]
            if faceDetectFPSQueue.full():
                try:
                    faceDetectFPSQueue.get_nowait()
                except:
                    pass
            try:
                faceDetectFPSQueue.put_nowait(len(frameTimeList))
            except:
                pass

def main():

    class CaptureDevice:
        def __init__(self) -> None:
            self.FPS = 0
            cameras = FilterGraph().get_input_devices()
            try:
                self.cap = cv2.VideoCapture(cameras.index(settings['camera']['name']))
            except:
                settings['camera']['name'] = cameras[0]
                with open('./settings.json', 'w', encoding='utf8') as f:
                    json.dump(settings , f)
                self.cap = cv2.VideoCapture(0)
            self.available_resolutions = self.get_camera_available_resolutions()
            if settings['camera']['resolution'] not in self.available_resolutions:
                settings['camera']['resolution'] = self.available_resolutions[-1]
                with open('./settings.json', 'w', encoding='utf8') as f:
                    json.dump(settings , f)
            self.processPool = multiprocessing.Pool(processes = 2)
            self.cameraFrameQueue = multiprocessing.Manager().Queue(1)
            self.cameraFPSQueue = multiprocessing.Manager().Queue(1)
            self.cam2faceQueue = multiprocessing.Manager().Queue(1)
            self.faceDetectFrameQueue = multiprocessing.Manager().Queue(1)
            self.faceDetectFPSQueue = multiprocessing.Manager().Queue(1)

        def start_get_camera_frame(self):
            self.getCameraFrameTask = self.processPool.apply_async(get_camera_frame_func , (settings['camera']['resolution'] , FilterGraph().get_input_devices().index(settings['camera']['name']) , self.cameraFrameQueue , self.cameraFPSQueue , self.cam2faceQueue))
            self.cameraFrame = self.cameraFrameQueue.get()
            self.cameraFPS = self.cameraFPSQueue.get()

        def start_face_detection(self):
            self.faceDetectTask = self.processPool.apply_async(get_face_detection_frame_func , (self.cam2faceQueue , self.faceDetectFrameQueue , self.faceDetectFPSQueue))
            self.faceDetectFrame = self.faceDetectFrameQueue.get()
            self.faceDetectFPS = self.faceDetectFPSQueue.get()

        def get_camera_available_resolutions(self):
            resolutions = []
            for res in COMMON_RESOLUTION:
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, res[0])
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, res[1])
                rw = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
                rh = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
                if rw == res[0] and rh == res[1]:
                    resolutions.append(list(res))
            return resolutions

    app = FastAPI()

    with open('./settings.json', 'r', encoding='utf8') as f:
        settings = json.load(f)

    global camera
    camera = CaptureDevice()
    camera.start_get_camera_frame()
    camera.start_face_detection()

    @app.get("/")
    async def read_root():
        with open('index.html' , 'r', encoding='utf8') as f:
            htmlContent = await asyncio.to_thread(f.read)
        return HTMLResponse(content=htmlContent, status_code=200)
    
    @app.get("/current_camera")
    def get_available_cameras():
        return {"current_camera": settings['camera']['name']}
    
    @app.get("/available_cameras")
    def get_available_cameras():
        #no directshow alternative https://github.com/pvys/CV-camera-finder
        return {"available_cameras": FilterGraph().get_input_devices()}
        
    @app.get("/camera_current_resolution")
    def get_camera_current_resolution():
        return {"camera_current_resolution": settings['camera']['resolution']}
    
    @app.get("/camera_available_resolutions")
    def get_camera_available_resolutions():
        global camera
        return {"camera_available_resolutions": camera.available_resolutions}
    
    @app.get("/camera_config")
    def camera_config(selectedCamera: str='' , resolution: str=''):
        global camera
        response = {}
        camera.processPool.terminate()
        cameras = FilterGraph().get_input_devices()
        resolution = list(resolution.partition('x'))
        del resolution[1]
        for i in (0 , 1):
            resolution[i] = int(resolution[i])
        if selectedCamera in cameras:
            settings['camera']['name'] = selectedCamera
            response['selectedCamera'] = 'OK'
        else:
            settings['camera']['name'] = cameras[0]
            response['selectedCamera'] = 'Camera not found, set to default.'
        camera = CaptureDevice()
        if resolution in camera.available_resolutions:
            settings['camera']['resolution'] = resolution
            response['cameraResolution'] = 'OK'
        else:
            settings['camera']['resolution'] = camera.available_resolutions[0]
            response['cameraResolution'] = 'Resolution unusable, set to default.'
        with open('./settings.json', 'w', encoding='utf8') as f:
            json.dump(settings , f)
        camera = CaptureDevice()
        camera.start_get_camera_frame()
        camera.start_face_detection()
    
    @app.get("/camera_frame")
    async def get_camera_frame():
        try:
            camera.cameraFrame = camera.cameraFrameQueue.get_nowait()
        except:     #若無新幀則跳過
            pass
        res , im_png = await asyncio.to_thread(cv2.imencode , ".jpg" , camera.cameraFrame , [cv2.IMWRITE_JPEG_QUALITY, 90])
        return StreamingResponse(io.BytesIO(im_png.tobytes()), media_type="image/jpg")
    
    @app.get("/camera_FPS")
    def get_camera_FPS():
        global camera
        try:
            camera.cameraFPS = camera.cameraFPSQueue.get_nowait()
        except:
            pass
        return {"camera_FPS": camera.cameraFPS}
    
    @app.get("/face_detection_frame")
    async def get_face_detection_frame():
        try:
            camera.faceDetectFrame = camera.faceDetectFrameQueue.get_nowait()
            camera.faceDetectFrame = cv2.cvtColor(camera.faceDetectFrame, cv2.COLOR_RGB2BGR)
        except:
            pass
        res , im_png = await asyncio.to_thread(cv2.imencode , ".jpg" , camera.faceDetectFrame , [cv2.IMWRITE_JPEG_QUALITY, 90])
        return StreamingResponse(io.BytesIO(im_png.tobytes()), media_type="image/jpg")
    
    @app.get("/CPU_usage")
    def get_CPU_usage():
        return {"CPU_usage": f'{psutil.cpu_percent(percpu=False)}%'}
    
    import uvicorn
    #import subprocess
    #subprocess.Popen(('python' , './frontend/start_frontend.py'))
    from frontend import start_frontend
    multiprocessing.Process(target=start_frontend.main).start()     #這執行方法才能打包 儘管Streamlit無法打包
    uvicorn.run(app , host='0.0.0.0' , port=8000 , log_level='warning')

if __name__ == '__main__':
    main()