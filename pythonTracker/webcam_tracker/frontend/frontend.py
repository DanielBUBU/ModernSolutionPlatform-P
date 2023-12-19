import streamlit
import pandas as pd
import asyncio , json , time , requests , io , threading
from urllib.parse import quote


async def main():

    class Server:
        def  __init__(self , address) -> None:
            self.address = address
            self.current_camera = ''
            self.available_cameras = ()
            self.camera_current_resolution = ''
            self.camera_available_resolutions = ()
            self.camera_FPS = ''
            self.CPU_usage = ''

        async def get_current_camera(self):
            response = await asyncio.to_thread(requests.get , f'{self.address}/current_camera')
            if response.status_code == 200:
                self.current_camera = json.loads(response.text)['current_camera']

        async def get_available_cameras(self):
            response = await asyncio.to_thread(requests.get , f'{self.address}/available_cameras')
            if response.status_code == 200:
                self.available_cameras = json.loads(response.text)['available_cameras']

        async def get_camera_current_resolution(self):
            response = await asyncio.to_thread(requests.get , f'{self.address}/camera_current_resolution')
            if response.status_code == 200:
                self.camera_current_resolution = json.loads(response.text)['camera_current_resolution']

        async def get_camera_available_resolutions(self):
            response = await asyncio.to_thread(requests.get , f'{self.address}/camera_available_resolutions')
            if response.status_code == 200:
                self.camera_available_resolutions = json.loads(response.text)['camera_available_resolutions']

        def camera_config(self , selectedCamera , selectedCameraResolution):        #配合Apply按鈕無法使用async
            selectedCamera = quote(selectedCamera)
            selectedCameraResolution = quote(selectedCameraResolution.strip(' ').lower())
            requests.get(f'{self.address}/camera_config?selectedCamera={selectedCamera}&resolution={selectedCameraResolution}')

        async def get_camera_frame(self):
            response = await asyncio.to_thread(requests.get , f'{self.address}/camera_frame' , stream = True)
            if response.status_code == 200:
                #https://gist.github.com/obskyr/b9d4b4223e7eaf4eedcd9defabb34f13
                bytes = io.BytesIO()
                bytes.seek(0, io.SEEK_END)
                for chunk in response.iter_content():
                    bytes.write(chunk)
                self.cameraFrame = bytes
            else:
                with open('loading.jpg' , 'rb') as f:
                    self.cameraFrame = f

        async def get_face_detection_frame(self):
            response = await asyncio.to_thread(requests.get , f'{self.address}/face_detection_frame' , stream = True)
            if response.status_code == 200:
                bytes = io.BytesIO()
                bytes.seek(0, io.SEEK_END)
                for chunk in response.iter_content():
                    bytes.write(chunk)
                self.faceDetectFrame = bytes
            else:
                with open('loading.jpg' , 'rb') as f:
                    self.faceDetectFrame = f

        async def get_camera_FPS(self):
            response = await asyncio.to_thread(requests.get , f'{self.address}/camera_FPS')
            if response.status_code == 200:
                self.camera_FPS = str(json.loads(response.text)['camera_FPS'])

        async def get_CPU_usage(self):
            response = await asyncio.to_thread(requests.get , f'{self.address}/CPU_usage')
            if response.status_code == 200:
                self.CPU_usage = str(json.loads(response.text)['CPU_usage'])

    #streamlit.session_state['camAvailableResolution'] = self.availableResolution

    server = Server('http://127.0.0.1:8000')

    streamlit.title('I\'m Gay')
    streamlit.write("So Do U")

    stframe = streamlit.empty()
    column1 , column2 = streamlit.columns(2)

    async with asyncio.TaskGroup() as tg:
        tg.create_task(server.get_current_camera())
        tg.create_task(server.get_available_cameras())
        tg.create_task(server.get_camera_current_resolution())
        tg.create_task(server.get_camera_available_resolutions())
        tg.create_task(server.get_camera_FPS())
        tg.create_task(server.get_CPU_usage())

    with column1:
        selectedCamera = streamlit.selectbox('Camera Select' , server.available_cameras , index=server.available_cameras.index(server.current_camera))
    with column2:
        default = server.camera_available_resolutions.index(server.camera_current_resolution)
        options = []
        for res in server.camera_available_resolutions:
            options.append(f'{res[0]} X {res[1]}')
        selectedCameraResolution = streamlit.selectbox('Resolution Select' , options , index=default)

    if streamlit.button('Apply' , on_click=server.camera_config , args=(selectedCamera , selectedCameraResolution)):
        streamlit.experimental_rerun()      #如果程式內有無窮迴圈，streamlit會卡bug導致按鈕按下後永遠回傳True，需要重新載入。https://github.com/streamlit/streamlit/issues/4595

    chart = streamlit.empty()

    lastRenewFrameTime = time.time()
    lastRenewInfoTime = time.time()

    while True:
        if time.time() - lastRenewFrameTime >= 0.0333:
            lastRenewFrameTime = time.time()
            #await server.get_camera_frame()
            await server.get_face_detection_frame()
            #stframe.image(server.cameraFrame)
            stframe.image(server.faceDetectFrame)
        if time.time() - lastRenewInfoTime >= 1:
            lastRenewInfoTime = time.time()
            async with asyncio.TaskGroup() as tg:
                tg.create_task(server.get_camera_FPS())
                tg.create_task(server.get_CPU_usage())
            chart.write(pd.DataFrame({'': ('camera FPS' , 'CPU usage'),'value': (server.camera_FPS , server.CPU_usage)}))

    #https://discuss.streamlit.io/t/streamlit-webcam-stream-processing-using-opencv-python-and-tensorflow/17753 https://github.com/whitphx/streamlit-webrtc

if __name__ == "__main__":
    asyncio.run(main())