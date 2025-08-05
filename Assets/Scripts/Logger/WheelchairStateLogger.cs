using UnityEngine;
using Simulator.Logging;

namespace Simulator.LoggingModules
{
    public class WheelchairState : MonoBehaviour, ILoggingProvider
    {
        private Vector3 lastPosition;
        private Vector3 currentVelocity;

        void Start()
        {
            lastPosition = transform.position;
        }

        void Update()
        {
            Vector3 currentPosition = transform.position;
            // not rb.linearVelocity, as contolled by ros2 Twist
            // and the velocity is not updated by physics engine
            // so calculate the velocity manually
            currentVelocity = (currentPosition - lastPosition) / Time.deltaTime; 
            lastPosition = currentPosition;
        }

        public string GetHeader()
        {
            // pos_x, pos_y, pos_z, rot_yaw, vel_x, vel_z
            // pos_x, pos_y, pos_z: position in world coordinates
            // rot_yaw: rotation around y-axis in degrees
            // vel_x, vel_z: velocity in world coordinates (x and z components)
            return "pos_x,pos_y,pos_z,rot_yaw,vel_x,vel_z";
        }

        public string GetLogLine()
        {
            Vector3 pos = transform.position;
            float yaw = transform.eulerAngles.y;

            return $"{pos.x:F3},{pos.y:F3},{pos.z:F3},{yaw:F1},{currentVelocity.x:F3},{currentVelocity.z:F3}";
        }
    }
}
