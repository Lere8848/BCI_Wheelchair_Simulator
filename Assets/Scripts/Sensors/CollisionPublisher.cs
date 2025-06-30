using UnityEngine;
using Unity.Robotics.ROSTCPConnector;
using RosMessageTypes.Std;


public class CollisionPublisher : MonoBehaviour
{
    public string topicName = "/collision_flag";

    private ROSConnection ros;
    private bool collisionDetected = false;

    // 发布间隔（秒），比如每0.5秒发布一次
    public float publishInterval = 0.5f; // 可以在Inspector中修改
    private float timeSinceLastPublish = 0f;

    void Start()
    {
        ros = ROSConnection.GetOrCreateInstance();
        ros.RegisterPublisher<BoolMsg>(topicName);
    }

    void FixedUpdate()
    {
        // 更新时间计数器
        timeSinceLastPublish += Time.fixedDeltaTime;

        // 到达发布间隔时才发布一次状态
        if (timeSinceLastPublish >= publishInterval)
        {
            // 创建消息并发布
            BoolMsg msg = new BoolMsg();
            msg.data = collisionDetected;
            ros.Publish(topicName, msg);

            // 重置标志位，等下一次碰撞触发再置True
            collisionDetected = false;

            // 重置计时器
            timeSinceLastPublish = 0f;
        }
    }

    void OnCollisionEnter(Collision collision)
    {
        // 发生碰撞时触发，将标志位置为True
        collisionDetected = true;
        Debug.Log("[CollisionDetector] Collision detected with: " + collision.gameObject.name);
    }
}
