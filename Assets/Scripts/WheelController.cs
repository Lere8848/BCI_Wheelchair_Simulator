using UnityEngine;

// 轮椅轮子控制器
// 该脚本控制轮椅的驱动轮和万向轮，处理扭矩和视觉效果
public class WheelController : MonoBehaviour
{
    [Header("Drive Wheels")]
    public WheelCollider leftWheelCollider;   // 左驱动轮碰撞体
    public WheelCollider rightWheelCollider;  // 右驱动轮碰撞体
    public Transform leftWheelMesh;           // 左驱动轮模型
    public Transform rightWheelMesh;          // 右驱动轮模型

    [Header("Caster Wheels (Visual Only)")]
    public Transform[] casterWheels;          // 万向轮模型（仅用于视觉效果）
    public float casterSpinFactor = 5f;       // 万向轮旋转因子

    [Header("Drive Parameters")]
    public float torqueScale = 150f;          // 扭矩缩放系数
    private float speed = 0f;                  // 线速度
    private float angular = 0f;                // 角速度

    private Vector3 lastPosition;             // 上一帧位置

    // 左右驱动轮的累计视觉旋转角
    private float leftWheelAngle = 0f;
    private float rightWheelAngle = 0f;

    void Start()
    {
        lastPosition = transform.position;    // 初始化上一帧位置
    }

    void FixedUpdate()
    {
        // 差速控制：根据线速度和角速度计算左右轮扭矩
        float leftTorque = (speed - angular * 0.5f) * torqueScale;
        float rightTorque = (speed + angular * 0.5f) * torqueScale;

        leftWheelCollider.motorTorque = leftTorque;
        rightWheelCollider.motorTorque = rightTorque;

        // 计算本帧前进方向的位移
        Vector3 delta = transform.position - lastPosition;
        float forwardMove = Vector3.Dot(delta, transform.forward);
        float wheelCircumference = 2 * Mathf.PI * leftWheelCollider.radius;
        float deltaAngle = (forwardMove / wheelCircumference) * 360f;

        // 累计角度（防止重复计算）
        leftWheelAngle += deltaAngle;
        rightWheelAngle += deltaAngle;

        // 更新驱动轮视觉效果
        UpdateWheelPose(leftWheelCollider, leftWheelMesh, leftWheelAngle);
        UpdateWheelPose(rightWheelCollider, rightWheelMesh, rightWheelAngle);

        // 旋转万向轮
        RotateCasterWheels(forwardMove);

        // 更新上一帧位置
        lastPosition = transform.position;
    }

    // 更新轮子的模型位置和旋转
    void UpdateWheelPose(WheelCollider collider, Transform mesh, float angle)
    {
        Vector3 pos;
        Quaternion rot;
        collider.GetWorldPose(out pos, out rot); // 获取轮子的世界位置和旋转
        mesh.position = pos;
        mesh.rotation = Quaternion.Euler(angle, 0, 0); // 绕X轴旋转
    }

    // 旋转万向轮（仅视觉效果）
    void RotateCasterWheels(float forwardMove)
    {
        foreach (Transform caster in casterWheels)
        {
            caster.Rotate(Vector3.right, forwardMove * casterSpinFactor * 100f); // 旋转万向轮
        }
    }

    // 被 ROS 调用来更新速度
    public void UpdateCmdVel(float linear, float angularZ)
    {
        speed = linear;      // 设置线速度
        angular = angularZ;  // 设置角速度
    }
}
