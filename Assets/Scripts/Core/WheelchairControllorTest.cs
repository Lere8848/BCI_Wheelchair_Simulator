using UnityEngine;
using Unity.Robotics.ROSTCPConnector;
using RosMessageTypes.Geometry;

public class WheelchairControllerTest : MonoBehaviour
{
    private ROSConnection ros;  // ROS connection instance
    public string topicName = "/cmd_vel"; // subscribed topic name

    public float linearScale = 1.0f;      // linear velocity scale factor
    public float angularScale = 100.0f;   // angular velocity scale factor (degrees/second)

    private float linearVelocity = 0f;    // current linear velocity
    private float angularVelocity = 0f;   // current angular velocity

    private Rigidbody rb;                 // Rigidbody component

    void Start()
    {
        rb = GetComponent<Rigidbody>();
        if (rb == null)
        {
            Debug.LogError("Rigidbody component missing from this GameObject.");
            return;
        }

        ros = ROSConnection.GetOrCreateInstance();
        ros.Subscribe<TwistMsg>(topicName, ReceiveVelocityCommand);

        Debug.Log("[Wheelchair] ROS connection established. Subscribed to: " + topicName);
    }

    // Callback function: receive Twist messages from /cmd_vel
    void ReceiveVelocityCommand(TwistMsg msg)
    {
        linearVelocity = (float)msg.linear.x * linearScale;
        angularVelocity = (float)msg.angular.z * angularScale;

        Debug.Log($"[Wheelchair] Received Twist: linear={linearVelocity:F2}, angular={angularVelocity:F2}");
    }

    void FixedUpdate()
    {
        if (rb == null)
            return;

        // Calculate displacement in the forward direction
        Vector3 move = transform.forward * linearVelocity * Time.fixedDeltaTime;
        rb.MovePosition(rb.position + move);

        // Calculate rotation around the Y-axis
        Quaternion turn = Quaternion.Euler(0f, angularVelocity * Time.fixedDeltaTime, 0f);
        rb.MoveRotation(rb.rotation * turn);
    }
}
