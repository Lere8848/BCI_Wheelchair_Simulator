using UnityEngine;
using Unity.Robotics.ROSTCPConnector;
using RosMessageTypes.Nav;
using RosMessageTypes.Geometry;
using Simulator.SimUtils;

public class OdomPublisher : MonoBehaviour
{
    [Header("Odometry Parameters")]
    public string topicName = "/odom"; // Topic name to publish
    public GameObject trackedObject;   // Object to track
    public string frameId = "odom";    // Frame ID
    public string childFrameId = "base_link"; // Child frame ID
    public float publishHz = 10.0f;    // Publishing frequency (Hz)

    [Header("Noise Control")]
    public bool enableNoise = false;
    public float linearNoiseStdDev = 0.02f;   // m/s
    public float angularNoiseStdDev = 0.05f;  // rad/s

    private Vector3 lastPosition;      // Last frame position
    private Quaternion lastRotation;   // Last frame rotation
    private Vector3 linearVelocity;    // Linear velocity
    private Vector3 angularVelocity;   // Angular velocity
    private float timer = 0f;          // Timer

    private ROSConnection ros;         // ROS connection instance

    void Start()
    {
        if (trackedObject == null)
            trackedObject = this.gameObject; // If no tracked object specified, default to self

        lastPosition = trackedObject.transform.position; // Initialize position
        lastRotation = trackedObject.transform.rotation; // Initialize rotation

        ros = ROSConnection.GetOrCreateInstance(); // Get or create ROS connection
        ros.RegisterPublisher<OdometryMsg>(topicName); // Register topic publisher
    }

    void Update()
    {
        timer += Time.deltaTime;
        if (timer >= 1.0f / publishHz) // Execute when publishing frequency is reached
        {
            timer = 0f;

            Vector3 currentPosition = trackedObject.transform.position; // Current frame position
            Quaternion currentRotation = trackedObject.transform.rotation; // Current frame rotation

            linearVelocity = (currentPosition - lastPosition) / Time.deltaTime; // Calculate linear velocity
            angularVelocity = SimUtils.CalculateAngularVelocity(lastRotation, currentRotation, Time.deltaTime); // Calculate angular velocity

            // Add noise
            if (enableNoise)
            {
                linearVelocity += new Vector3(
                    SimUtils.GenerateGaussianNoise() * linearNoiseStdDev,
                    0f,
                    SimUtils.GenerateGaussianNoise() * linearNoiseStdDev
                );

                angularVelocity += new Vector3(
                    0f,
                    0f,
                    SimUtils.GenerateGaussianNoise() * angularNoiseStdDev
                );
            }

            PublishOdom(currentPosition, currentRotation, linearVelocity, angularVelocity); // Publish odometry message

            lastPosition = currentPosition; // Update last frame position
            lastRotation = currentRotation; // Update last frame rotation
        }
    }

    // Publish odometry message
    void PublishOdom(Vector3 pos, Quaternion rot, Vector3 linVel, Vector3 angVel)
    {
        OdometryMsg msg = new OdometryMsg
        {
            header = new RosMessageTypes.Std.HeaderMsg
            {
                frame_id = frameId,
                stamp = new RosMessageTypes.BuiltinInterfaces.TimeMsg()
            },
            child_frame_id = childFrameId,
            pose = new PoseWithCovarianceMsg
            {
                pose = new PoseMsg
                {
                    position = new PointMsg(pos.x, pos.y, pos.z),
                    orientation = new QuaternionMsg(rot.x, rot.y, rot.z, rot.w)
                }
            },
            twist = new TwistWithCovarianceMsg
            {
                twist = new TwistMsg
                {
                    linear = new Vector3Msg(linVel.x, linVel.y, linVel.z),
                    angular = new Vector3Msg(angVel.x, angVel.y, angVel.z)
                }
            }
        };

        ros.Publish(topicName, msg); // Publish message to ROS
    }
}
