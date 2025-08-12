using UnityEngine;
using Unity.Robotics.ROSTCPConnector;
using RosMessageTypes.Sensor;
using Simulator.SimUtils;

public class UltrasonicPublisher : MonoBehaviour
{
    [Header("Ultrasonic Sensor Parameters")]
    [Tooltip("May use the /ultrasonic_<id> naming format, e.g., /ultrasonic_front")]
    public string topicName; // ROS topic name
    public float maxRange = 3.0f; // Maximum measurement range
    public float minRange = 0.05f; // Minimum measurement range
    public float publishHz = 10.0f; // Publishing frequency (Hz)

    [Header("Noise Control")]
    public bool enableNoise = false; // Whether to enable noise
    public float noiseStdDev = 0.01f; // Noise standard deviation

    private ROSConnection ros; // ROS connection instance
    private float timer = 0f; // Timer

    void Start()
    {
        ros = ROSConnection.GetOrCreateInstance(); // Get or create ROS connection instance
        ros.RegisterPublisher<RangeMsg>(topicName); // Register topic publisher
    }

    void Update()
    {
        timer += Time.deltaTime; // Update time
        if (timer >= 1f / publishHz) // Reached publishing cycle
        {
            timer = 0f;
            PublishUltrasonic(); // Publish ultrasonic data
        }

        // Debug.DrawRay(transform.position, transform.forward * maxRange, Color.yellow);
    }

    // Publish ultrasonic ranging message
    void PublishUltrasonic()
    {
        float distance = maxRange; // Default distance is maximum value
        Ray ray = new Ray(transform.position, transform.forward); // Cast ray forward from sensor position

        if (Physics.Raycast(ray, out RaycastHit hit, maxRange)) // Check if any object is hit by the ray
        {
            distance = hit.distance; // Get collision point distance
        }

        if (enableNoise) // If noise is enabled
        {
            float noise = SimUtils.GenerateGaussianNoise() * noiseStdDev; // Generate Gaussian noise
            distance = Mathf.Clamp(distance + noise, minRange, maxRange); // Limit distance within valid range
        }

        // Construct Range message
        RangeMsg msg = new RangeMsg
        {
            header = new RosMessageTypes.Std.HeaderMsg
            {
                frame_id = this.gameObject.name, // Frame ID is current object name
                stamp = new RosMessageTypes.BuiltinInterfaces.TimeMsg() // Timestamp
            },
            radiation_type = RangeMsg.ULTRASOUND, // Radiation type is ultrasonic
            field_of_view = 0.2f, // Field of view (optional, simulates narrow beam angle)
            min_range = minRange, // Minimum measurement range
            max_range = maxRange, // Maximum measurement range
            range = distance // Actual measurement distance
        };
        Debug.DrawRay(transform.position, transform.forward * distance, Color.cyan, 0.1f); // Draw ray in scene
        // Debug.Log($"[ULTRASONIC] position: {transform.position}, direction: {transform.forward}");

        ros.Publish(topicName, msg); // Publish message to ROS
    }
}
