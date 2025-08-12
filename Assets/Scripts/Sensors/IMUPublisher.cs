using UnityEngine;
using Unity.Robotics.ROSTCPConnector;
using RosMessageTypes.Sensor;
using RosMessageTypes.Geometry;
using Simulator.SimUtils;

public class IMUPublisher : MonoBehaviour
{
    [Header("IMU Sensor Parameters")]
    public string topicName = "/imu/data"; // ROS topic name for publishing
    public Rigidbody trackedRigidbody;     // Rigidbody to track
    public float publishHz = 20.0f;        // Publishing frequency (Hz)

    [Header("Noise Control")]
    public bool enableNoise = false;       // Whether to enable noise
    public float linearNoiseStdDev = 0.1f;   // Linear acceleration noise standard deviation (m/s²)
    public float angularNoiseStdDev = 0.01f; // Angular velocity noise standard deviation (rad/s)

    private ROSConnection ros; // ROS connection instance
    private float timer;       // Timer

    void Start()
    {
        ros = ROSConnection.GetOrCreateInstance(); // Get or create ROS connection instance
        ros.RegisterPublisher<ImuMsg>(topicName);  // Register IMU message publisher

        if (trackedRigidbody == null)
            trackedRigidbody = GetComponent<Rigidbody>(); // Get rigidbody component
    }

    void Update()
    {
        timer += Time.deltaTime; // Accumulate time
        if (timer >= 1.0f / publishHz) // Reached publishing cycle
        {
            timer = 0f;
            PublishIMU(); // Publish IMU data
        }
    }

    // Publish IMU data to ROS
    void PublishIMU()
    {
        // Calculate linear acceleration and angular velocity
        Vector3 linAcc = trackedRigidbody.linearVelocity / Time.fixedDeltaTime;
        Vector3 angVel = trackedRigidbody.angularVelocity;

        // If noise is enabled, add Gaussian noise
        if (enableNoise)
        {
            linAcc += new Vector3(
                SimUtils.GenerateGaussianNoise() * linearNoiseStdDev,
                SimUtils.GenerateGaussianNoise() * linearNoiseStdDev,
                SimUtils.GenerateGaussianNoise() * linearNoiseStdDev
            );

            angVel += new Vector3(
                SimUtils.GenerateGaussianNoise() * angularNoiseStdDev,
                SimUtils.GenerateGaussianNoise() * angularNoiseStdDev,
                SimUtils.GenerateGaussianNoise() * angularNoiseStdDev
            );
        }

        // Construct IMU message
        ImuMsg msg = new ImuMsg
        {
            header = new RosMessageTypes.Std.HeaderMsg
            {
                frame_id = "imu_link", // Coordinate frame ID
                stamp = new RosMessageTypes.BuiltinInterfaces.TimeMsg() // Timestamp
            },
            orientation = new QuaternionMsg(),  // Can be supplemented if orientation estimation is needed
            angular_velocity = new Vector3Msg(angVel.x, angVel.y, angVel.z), // Angular velocity
            linear_acceleration = new Vector3Msg(linAcc.x, linAcc.y, linAcc.z), // Linear acceleration
            orientation_covariance = new double[9], // Orientation covariance
            angular_velocity_covariance = new double[9], // Angular velocity covariance
            linear_acceleration_covariance = new double[9] // Linear acceleration covariance
        };

        ros.Publish(topicName, msg); // Publish message to ROS
    }
}
