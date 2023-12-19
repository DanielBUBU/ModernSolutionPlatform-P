// Copyright (c) Microsoft Corporation. All rights reserved.
// Licensed under the MIT License.
//
// cd D:\AirSimNH\WindowsNoEditor
//./AirSimNH.exe -settings="D:\AirSimNH\WindowsNoEditor\settings.json"

#include "common/common_utils/StrictMode.hpp"
STRICT_MODE_OFF
#ifndef RPCLIB_MSGPACK
#define RPCLIB_MSGPACK clmdep_msgpack
#endif // !RPCLIB_MSGPACK
#include "rpc/rpc_error.h"
STRICT_MODE_ON

#include "vehicles/multirotor/api/MultirotorRpcLibClient.hpp"
#include "common/common_utils/FileSystem.hpp"
#include <iostream>
#include <chrono>
#include <thread>
#define MY_PI 3.14159265358979323846
using namespace msr::airlib;
using namespace std;
void stbFunc(MultirotorRpcLibClient& client, bool& goFlag, float targetX, float targetY, float targetZ)
{
    Quaternionr q;
    Vector3r v3r(0.0, 0.0, 0.0);
    Pose camera_pose;
    TTimePoint prevTS = client.getImuData("Imu", "SimpleFlight").time_stamp;
    float prevX = 0;
    float prevY = 0;
    float prevZ = 0;
    //stable
    while (goFlag) {
        MultirotorState ms = client.getMultirotorState("SimpleFlight");
        ImuBase::Output ImuData = client.getImuData("Imu", "SimpleFlight");
        Vector3r euler = ImuData.orientation.toRotationMatrix().eulerAngles(2, 1, 0);
        float dx = targetX - ms.getPosition().x();
        float dy = targetY - ms.getPosition().y();
        float dz = targetZ - ms.getPosition().z();

        //float dt = ((float)prevTS - (float)ImuData.time_stamp) / 1000000; //in second
        float predictConstant = (float)0.6;

        prevX = (1 - predictConstant) * ImuData.angular_velocity.x() + predictConstant * (prevX);
        prevY = (1 - predictConstant) * ImuData.angular_velocity.y() + predictConstant * (prevY);
        prevZ = (1 - predictConstant) * ImuData.angular_velocity.z() + predictConstant * (prevZ);

        //cout << prevTS << endl;
        //float predictX = dt * prevX;
        //float predictY = dt * prevY;
        //float predictZ = dt * prevZ;

        float qx = -euler.z(); //+ predictX;
        float qy = -euler.y(); //+ predictY;
        float qz = -euler.x(); //+ predictZ;
        //cout << qx << "," << qy << "," << qz;
        qz = fmod(qz + atan2f(dy, dx), 2 * (float)MY_PI);
        float dxy = abs(sqrt(powf(abs(dx), 2) + powf(abs(dy), 2))); //distance on xy
        float dqy = atan2f(dz, dxy);
        if (qy <= -MY_PI / 2) {
            qy += dqy;
            //-predictY;
            //cout << "DD" << endl;
        }
        else if (qy >= MY_PI / 2) {
            qy += dqy;
            //+predictY;
            //cout << "KK" << endl;
        }
        else {
            qy -= dqy;
            //-predictY;
        }

        q = AngleAxisr(qz, Vector3r::UnitZ()) * AngleAxisr(qy, Vector3r::UnitY()) * AngleAxisr(qx, Vector3r::UnitX());
        camera_pose = Pose(v3r, q);

        client.simSetCameraPose("0", camera_pose, "SimpleFlight", false);

        prevTS = ImuData.time_stamp;
        //this_thread::yield();
    }
    return;
}

Vector3r getTargetCoordinate(MultirotorRpcLibClient& client, float distance)
{
    MultirotorState ms = client.getMultirotorState("SimpleFlight");
    ImuBase::Output ImuData = client.getImuData("Imu", "SimpleFlight");
    Quaternionr droneQuaternion = ms.getOrientation();
    Quaternionr sensorOrientation = client.getDistanceSensorData("Distance", "SimpleFlight").relative_pose.orientation; //讀取測距儀姿態
    //三軸方向向量(以單位向量表示)
    //cout << "sensorOrientation = " << sensorOrientation << endl;
    Matrix3x3r droneRotationMatrix = droneQuaternion.toRotationMatrix();
    Matrix3x3r distanceRotationMatrix = sensorOrientation.toRotationMatrix();
    Quaternionr q = droneQuaternion * sensorOrientation;
    Matrix3x3r resultRotationMatrix = droneRotationMatrix * distanceRotationMatrix;
    cout << "rotationMatrix = " << resultRotationMatrix << endl;
    cout << "qRotationMatrix = " << q.toRotationMatrix() << endl;

    Vector3r xAxis = resultRotationMatrix.col(0); //x方向向量
    cout << "xAxis = " << xAxis << endl;
    Vector3r yAxis = resultRotationMatrix.col(1); //y方向向量
    cout << "yAxis = " << yAxis << endl;
    Vector3r zAxis = resultRotationMatrix.col(2); //z方向向量
    cout << "zAxis = " << zAxis << endl;

    Vector3r dronePosition = client.getMultirotorState("SimpleFlight").getPosition();
    Vector3r targetPosition;
    targetPosition = distance * xAxis;
    targetPosition += dronePosition;
    //目標座標為 :
    cout << "Target position (" << targetPosition << ")" << endl;
    return targetPosition;
}

int main()
{
    MultirotorRpcLibClient client;
    typedef ImageCaptureBase::ImageRequest ImageRequest;
    typedef ImageCaptureBase::ImageResponse ImageResponse;
    typedef ImageCaptureBase::ImageType ImageType;
    typedef common_utils::FileSystem FileSystem;

    client.confirmConnection();

    Vector3r position = client.getMultirotorState().getPosition();
    float z = 0.0;
    //position.z(); // current position (NED coordinate system).
    constexpr float speed = 5.0f;
    constexpr float size = 25.0f;
    constexpr float duration = size / speed;
    DrivetrainType drivetrain = DrivetrainType::ForwardOnly;
    YawMode yaw_mode(true, 0);
    //Quaternion parameter
    float qx = 0.0;
    float qy = 0.0;
    float qz = 0.0;
    bool goFlag = false;

    //測試用
    cout << client.listVehicles()[0] << "  " << client.listVehicles().size() << endl;
    cout << "Testing start" << endl;
    client.enableApiControl(true);
    client.armDisarm(true);

    //takeoff
    float takeoff_timeout = 5;
    client.takeoffAsync(takeoff_timeout)->waitOnLastTask();
    this_thread::sleep_for(chrono::duration<double>(takeoff_timeout));

    //hint
    cout << "w : forward\na : turn left\ns : backward\nd : turn right\n";
    cout << "r : up\nf : down\nc : camera position setting\nz : get focus distance\n";
    cout << "q : land and quit\n";

    //operation
    bool exit = FALSE;
    thread* stbThread = nullptr;
    char direction = 'w'; //direction of drone, default is forward
    msr::airlib::DistanceSensorData distanceData;
    float distance;
    Vector3r targetP;

    while (exit == FALSE) {
        //hover
        client.hoverAsync()
            ->waitOnLastTask();
        Quaternionr q;

        Vector3r v3r(0.0, 0.0, 0.0);
        Pose camera_pose;
        char command;

        cout << "input your operation : ";
        cin >> command;
        switch (command) {
        case 'e':
            //forward
            direction = 'w';
            std::cout << "moveByVelocity(" << speed << ", 0, " << z << "," << duration << ")" << std::endl;
            client.rotateByYawRateAsync(speed, duration, "SimpleFlight")->waitOnLastTask();
            //std::this_thread::sleep_for(std::chrono::duration<double>(duration));
            break;
        case 'q':
            //forward
            direction = 'w';
            std::cout << "moveByVelocity(" << speed << ", 0, " << z << "," << duration << ")" << std::endl;
            client.rotateByYawRateAsync(-speed, duration, "SimpleFlight")->waitOnLastTask();
            //std::this_thread::sleep_for(std::chrono::duration<double>(duration));
            break;
        case 'w':
            //forward
            direction = 'w';
            std::cout << "moveByVelocity(" << speed << ", 0, " << z << "," << duration << ")" << std::endl;
            client.moveByVelocityAsync(speed, 0, 0, duration, drivetrain, yaw_mode)->waitOnLastTask();
            //std::this_thread::sleep_for(std::chrono::duration<double>(duration));
            break;
        case 'a':
            //left
            direction = 'a';
            std::cout << "moveByVelocity(0, " << -speed << "," << z << "," << duration << ")" << std::endl;
            client.moveByVelocityAsync(0, -speed, 0, duration, drivetrain, yaw_mode)->waitOnLastTask();
            //std::this_thread::sleep_for(std::chrono::duration<double>(duration));
            break;
        case 's':
            //backward
            direction = 's';
            client.hoverAsync()->waitOnLastTask();
            std::cout << "moveByVelocity(" << -speed << ", 0, " << z << "," << duration << ")" << std::endl;
            client.moveByVelocityAsync(-speed, 0, 0, duration, drivetrain, yaw_mode)->waitOnLastTask();
            // std::this_thread::sleep_for(std::chrono::duration<double>(duration));
            break;
        case 'd':
            //right
            direction = 'd';
            std::cout << "moveByVelocity(0, " << speed << "," << z << "," << duration << ")" << std::endl;
            client.moveByVelocityAsync(0, speed, 0, duration, drivetrain, yaw_mode)->waitOnLastTask();
            //std::this_thread::sleep_for(std::chrono::duration<double>(duration));
            break;
        case 'r':
            //up
            std::cout << "moveByVelocity("
                << "0"
                << ", 0, " << -speed << "," << duration << ")" << std::endl;
            client.moveByVelocityAsync(0, 0, -speed, duration, drivetrain, yaw_mode)->waitOnLastTask();
            //std::this_thread::sleep_for(std::chrono::duration<double>(duration));
            break;
        case 'f':
            //down
            std::cout << "moveByVelocity("
                << "0"
                << ", 0, " << speed << "," << duration << ")" << std::endl;
            client.moveByVelocityAsync(0, 0, speed, duration, drivetrain, yaw_mode)->waitOnLastTask();
            //std::this_thread::sleep_for(std::chrono::duration<double>(duration));
            break;
        case 'c':
            //camera set
            cin >> qx >> qy >> qz;
            q = AngleAxisr(qz, Vector3r::UnitZ()) * AngleAxisr(qy, Vector3r::UnitY()) * AngleAxisr(qx, Vector3r::UnitX());
            camera_pose = Pose(v3r, q);
            client.simSetCameraPose("0", camera_pose, "SimpleFlight", false);

            break;
        case 'z':
            //measure distance
            cout << "Drone position : (" << client.getMultirotorState().getPosition().x() << ",  " << client.getMultirotorState().getPosition().y() << ", " << client.getMultirotorState().getPosition().z() << ")" << std::endl;
            distanceData = client.getDistanceSensorData("Distance", "SimpleFlight");
            distance = distanceData.distance;
            cout << "measured distance : " << distance << endl;
            getTargetCoordinate(client, distance);
            break;
        case 'l':
            //quit and land
            cout << "Landing!!!" << endl;
            client.landAsync()->waitOnLastTask();
            cout << "Test Over!!!!" << endl;
            exit = TRUE;
            break;
        case 'b':
            //
            distanceData = client.getDistanceSensorData("Distance", "SimpleFlight");
            distance = distanceData.distance;
            cout << "measured distance : " << distance << endl;
            targetP = getTargetCoordinate(client, distance);
            if (stbThread == nullptr) {
                goFlag = true;
                switch (direction) {
                case 'w':
                    break;
                case 'a':
                    break;
                case 's':
                    break;
                case 'd':
                    break;
                default:
                    break;
                }
                stbThread = new thread(stbFunc, ref(client), ref(goFlag), targetP.x(), targetP.y(), targetP.z());
            }
            break;
        case 'n':
            //
            goFlag = false;
            if ((*stbThread).joinable()) {
                (*stbThread).join();
                stbThread = nullptr;
            }
            break;
        default:
            cout << "Command unavaliable" << endl;
            break;
        }

        //cout << "X:" << client.getMultirotorState("SimpleFlight").kinematics_estimated.pose.position.x() << "Y:" << client.getMultirotorState("SimpleFlight").kinematics_estimated.pose.position.y() << "Z:" << client.getMultirotorState("SimpleFlight").kinematics_estimated.pose.position.z() << endl;

        /*
        std::cout << "Press Enter to get FPV image" << std::endl;
        std::cin.get();
        const std::vector<ImageRequest> request{ ImageRequest("0", ImageType::Scene), ImageRequest("1", ImageType::DepthPlanar, true) };
        const std::vector<ImageResponse>& response = client.simGetImages(request);
        std::cout << "# of images received: " << response.size() << std::endl;
 if (!response.size()) {
            std::cout << "Enter path with ending separator to save images (leave empty for no save)" << std::endl;
            std::string path;
            std::getline(std::cin, path);
            for (const ImageResponse& image_info : response) {
                std::cout << "Image uint8 size: " << image_info.image_data_uint8.size() << std::endl;
                std::cout << "Image float size: " << image_info.image_data_float.size() << std::endl;
                if (path != "") {
                    std::string file_path = FileSystem::combine(path, std::to_string(image_info.time_stamp));
                    if (image_info.pixels_as_float) {
                        Utils::writePFMfile(image_info.image_data_float.data(), image_info.width, image_info.height, file_path + ".pfm");
                    }
                    else {
                        std::ofstream file(file_path + ".png", std::ios::binary);
                        file.write(reinterpret_cast<const char*>(image_info.image_data_uint8.data()), image_info.image_data_uint8.size());
                        file.close();
                    }
                }
            }
        }
        std::cout << "Press Enter to arm the drone" << std::endl;
        std::cin.get();
        client.armDisarm(true);
        //氣壓
        auto barometer_data = client.getBarometerData();
        std::cout << "Barometer data \n"
                  << "barometer_data.time_stamp \t" << barometer_data.time_stamp << std::endl
                  << "barometer_data.altitude \t" << barometer_data.altitude << std::endl
                  << "barometer_data.pressure \t" << barometer_data.pressure << std::endl
                  << "barometer_data.qnh \t" << barometer_data.qnh << std::endl;
        //慣性
        auto imu_data = client.getImuData();
        std::cout << "IMU data \n"
                  << "imu_data.time_stamp \t" << imu_data.time_stamp << std::endl
                  << "imu_data.orientation \t" << imu_data.orientation << std::endl
                  << "imu_data.angular_velocity \t" << imu_data.angular_velocity << std::endl
                  << "imu_data.linear_acceleration \t" << imu_data.linear_acceleration << std::endl;
        //gps
        auto gps_data = client.getGpsData();
        std::cout << "GPS data \n"
                  << "gps_data.time_stamp \t" << gps_data.time_stamp << std::endl
                  << "gps_data.gnss.time_utc \t" << gps_data.gnss.time_utc << std::endl
                  << "gps_data.gnss.geo_point \t" << gps_data.gnss.geo_point << std::endl
                  << "gps_data.gnss.eph \t" << gps_data.gnss.eph << std::endl
                  << "gps_data.gnss.epv \t" << gps_data.gnss.epv << std::endl
                  << "gps_data.gnss.velocity \t" << gps_data.gnss.velocity << std::endl
                  << "gps_data.gnss.fix_type \t" << gps_data.gnss.fix_type << std::endl;
        //磁力
        auto magnetometer_data = client.getMagnetometerData();
        std::cout << "Magnetometer data \n"
                  << "magnetometer_data.time_stamp \t" << magnetometer_data.time_stamp << std::endl
                  << "magnetometer_data.magnetic_field_body \t" << magnetometer_data.magnetic_field_body << std::endl;
        // << "magnetometer_data.magnetic_field_covariance" << magnetometer_data.magnetic_field_covariance // not implemented in sensor
        //takeoff
        std::cout << "Press Enter to takeoff" << std::endl;
        std::cin.get();
        takeoff_timeout = 5;
        client.takeoffAsync(takeoff_timeout)->waitOnLastTask();
        // switch to explicit hover mode so that this is the fall back when
        // move* commands are finished.
        std::this_thread::sleep_for(std::chrono::duration<double>(5));
        client.hoverAsync()->waitOnLastTask();
        std::cout << "Press Enter to fly in a 10m box pattern at 3 m/s velocity" << std::endl;
        std::cin.get();
        // moveByVelocityZ is an offboard operation, so we need to set offboard mode.
        client.enableApiControl(true);
        std::cout << "moveByVelocityZ(" << speed << ", 0, " << z << "," << duration << ")" << std::endl;
        client.moveByVelocityZAsync(speed, 0, z, duration, drivetrain, yaw_mode);
        std::this_thread::sleep_for(std::chrono::duration<double>(duration));
        std::cout << "moveByVelocityZ(0, " << speed << "," << z << "," << duration << ")" << std::endl;
        client.moveByVelocityZAsync(0, speed, z, duration, drivetrain, yaw_mode);
        std::this_thread::sleep_for(std::chrono::duration<double>(duration));
        std::cout << "moveByVelocityZ(" << -speed << ", 0, " << z << "," << duration << ")" << std::endl;
        client.moveByVelocityZAsync(-speed, 0, z, duration, drivetrain, yaw_mode);
        std::this_thread::sleep_for(std::chrono::duration<double>(duration));
        std::cout << "moveByVelocityZ(0, " << -speed << "," << z << "," << duration << ")" << std::endl;
        client.moveByVelocityZAsync(0, -speed, z, duration, drivetrain, yaw_mode);
        std::this_thread::sleep_for(std::chrono::duration<double>(duration));
        client.hoverAsync()->waitOnLastTask();
        std::cout << "Press Enter to land" << std::endl;
        std::cin.get();
        client.landAsync()->waitOnLastTask();
        std::cout << "Press Enter to disarm" << std::endl;
        std::cin.get();
        client.armDisarm(false);*/
    }
    /*  catch (rpc::rpc_error& e) {
        const auto msg = e.get_error().as<std::string>();
        std::cout << "Exception raised by the API, something went wrong." << std::endl
                  << msg << std::endl;
    }*/

    return 0;
}