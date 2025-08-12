using UnityEngine;
using Unity.Robotics.ROSTCPConnector;
using RosMessageTypes.Std;


public class CollisionPublisher : MonoBehaviour
{
    public string topicName = "/collision_flag";

    private ROSConnection ros;
    private bool collisionDetected = false;

    // Publish interval (seconds), e.g., publish once every 0.5 seconds
    public float publishInterval = 0.5f; // Can be modified in Inspector
    private float timeSinceLastPublish = 0f;

    // Collision time to ignore at startup (seconds), to avoid false collision triggers during startup
    public float ignoreInitialCollisionTime = 0.5f; // Can be modified in Inspector
    private float startTime;

    void Start()
    {
        ros = ROSConnection.GetOrCreateInstance();
        ros.RegisterPublisher<BoolMsg>(topicName);

        // Initialize timer
        timeSinceLastPublish = 0f;
        // Record start time to avoid false collision triggers during startup
        startTime = Time.time;
    }

    void FixedUpdate()
    {
        // Update time counter
        timeSinceLastPublish += Time.fixedDeltaTime;

        // Only publish status when publish interval is reached
        if (timeSinceLastPublish >= publishInterval)
        {
            // Create message and publish
            BoolMsg msg = new BoolMsg();
            msg.data = collisionDetected;
            ros.Publish(topicName, msg);

            // Reset flag, wait for next collision to trigger and set to True
            collisionDetected = false;

            // Reset timer
            timeSinceLastPublish = 0f;
        }
    }

    void OnCollisionEnter(Collision collision)
    {
        // If collision occurs within the ignore time at startup, don't process it
        if (Time.time - startTime < ignoreInitialCollisionTime)
        {
            Debug.Log("[CollisionDetector] Ignored startup collision with: " + collision.gameObject.name);
            return;
        }

        // When collision occurs, set flag to True
        collisionDetected = true;
        Debug.Log("[CollisionDetector] Collision detected with: " + collision.gameObject.name);
    }
}
