using UnityEngine;

// Wheelchair wheel controller
// This script controls the wheelchair's drive wheels and caster wheels, handling torque and visual effects
public class WheelController : MonoBehaviour
{
    [Header("Drive Wheels")]
    public WheelCollider leftWheelCollider;   // Left drive wheel collider
    public WheelCollider rightWheelCollider;  // Right drive wheel collider
    public Transform leftWheelMesh;           // Left drive wheel model
    public Transform rightWheelMesh;          // Right drive wheel model

    [Header("Caster Wheels (Visual Only)")]
    public Transform[] casterWheels;          // Caster wheel models (visual effects only)
    public float casterSpinFactor = 5f;       // Caster wheel rotation factor

    [Header("Drive Parameters")]
    public float torqueScale;          // Torque scaling factor
    private float speed = 0f;                  // Linear velocity
    private float angular = 0f;                // Angular velocity

    private Vector3 lastPosition;             // Previous frame position

    // Accumulated visual rotation angles for left and right drive wheels
    private float leftWheelAngle = 0f;
    private float rightWheelAngle = 0f;

    void Start()
    {
        lastPosition = transform.position;    // Initialize previous frame position
    }

    void FixedUpdate()
    {
        // Differential control: calculate left and right wheel torque based on linear and angular velocity
        float leftTorque = (speed - angular * 0.5f) * torqueScale;
        float rightTorque = (speed + angular * 0.5f) * torqueScale;

        leftWheelCollider.motorTorque = leftTorque;
        rightWheelCollider.motorTorque = rightTorque;

        // Calculate displacement in the forward direction for this frame
        Vector3 delta = transform.position - lastPosition;
        float forwardMove = Vector3.Dot(delta, transform.forward);
        float wheelCircumference = 2 * Mathf.PI * leftWheelCollider.radius;
        float deltaAngle = (forwardMove / wheelCircumference) * 360f;

        // Accumulate angles (prevent duplicate calculations)
        leftWheelAngle += deltaAngle;
        rightWheelAngle += deltaAngle;

        // Update drive wheel visual effects
        UpdateWheelPose(leftWheelCollider, leftWheelMesh, leftWheelAngle);
        UpdateWheelPose(rightWheelCollider, rightWheelMesh, rightWheelAngle);

        // Rotate caster wheels
        RotateCasterWheels(forwardMove);

        // Update previous frame position
        lastPosition = transform.position;
    }

    // Update wheel model position and rotation
    void UpdateWheelPose(WheelCollider collider, Transform mesh, float angle)
    {
        Vector3 pos;
        Quaternion rot;
        collider.GetWorldPose(out pos, out rot); // Get wheel's world position and rotation
        mesh.position = pos;
        mesh.rotation = rot;
    }

    // Rotate caster wheels (visual effects only)
    void RotateCasterWheels(float forwardMove)
    {
        foreach (Transform caster in casterWheels)
        {
            caster.Rotate(Vector3.right, forwardMove * casterSpinFactor * 100f); // Rotate caster wheels
        }
    }

    // Called by ROS to update velocity
    public void UpdateCmdVel(float linear, float angularZ)
    {
        speed = linear;      // Set linear velocity
        angular = angularZ;  // Set angular velocity
    }
}
