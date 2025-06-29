using UnityEngine;
using Simulator.Sensors;

namespace Simulator.Core
{
    public class SensorManager : MonoBehaviour
    {
        [Header("Sensor Activation Control")]
        public bool lidarEnabled = true;
        public bool odomEnabled = true;
        public bool ultrasonicEnabled = true;
        public bool imuEnabled = true;
        public bool collisionEnabled = true;
        public bool cameraEnabled = true;

        void Start()
        {
            ToggleAllSensors();
        }

        void ToggleAllSensors()
        {
            // Lidar
            foreach (var lidar in FindObjectsByType<LidarPublisher>(FindObjectsSortMode.None))
                lidar.enabled = lidarEnabled;

            // odometry
            foreach (var odom in FindObjectsByType<OdomPublisher>(FindObjectsSortMode.None))
                odom.enabled = odomEnabled;

            // ultrasonic
            foreach (var ultra in FindObjectsByType<UltrasonicPublisher>(FindObjectsSortMode.None))
                ultra.enabled = ultrasonicEnabled;

            // IMU
            foreach (var imu in FindObjectsByType<IMUPublisher>(FindObjectsSortMode.None))
                imu.enabled = imuEnabled;

            // detection collision
            foreach (var collision in FindObjectsByType<CollisionPublisher>(FindObjectsSortMode.None))
                collision.enabled = collisionEnabled;

            // camera
            foreach (var cam in FindObjectsByType<CameraPublisher>(FindObjectsSortMode.None))
                cam.enabled = cameraEnabled;
        }
    }
}
