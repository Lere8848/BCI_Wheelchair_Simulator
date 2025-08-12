using Unity.Robotics.ROSTCPConnector;
using RosMessageTypes.Geometry;
using UnityEngine;

// This script subscribes to the /cmd_vel topic and updates the WheelController with the received velocity commands.
// could be extended later
public class WheelCmdVelSubscriber : MonoBehaviour
{
    public WheelController controller;

    void Start()
    {
        // If the /cmd_vel topic is no longer used in the future, remember to modify the subscription topic and message format here.
        ROSConnection.GetOrCreateInstance().Subscribe<TwistMsg>(
            "/cmd_vel",
            msg =>
            {
                float linear = (float)msg.linear.x;
                float angular = (float)msg.angular.z;
                controller.UpdateCmdVel(linear, angular);
            });
    }
}
