using UnityEngine;
using Unity.Robotics.ROSTCPConnector;
using RosGeometry = RosMessageTypes.Geometry;

public class AttractorVisualizer : MonoBehaviour
{
    [Header("Attractor Visualization Settings")]
    public GameObject attractorPrefab;  // 吸引子prefab
    public Transform wheelchairTransform;  // 轮椅的Transform引用
    public float visualScale = 1.0f;    // 可视化缩放系数
    public string topicName = "/attractor_pos"; // ROS话题名称

    [Header("Pulse Animation Settings")]
    public bool enablePulseAnimation = true;     // 启用脉冲动画
    public float pulseSpeed = 2.0f;             // 脉冲速度
    public float pulseScale = 0.2f;             // 脉冲幅度

    private GameObject attractorObject;  // 当前吸引子对象
    private Vector3 originalScale;       // 原始缩放
    private bool isAttractorActive = false;
    private Vector3 relativeAttractorPos;  // 相对于轮椅的吸引子位置

    void Start()
    {
        // 订阅ROS话题
        ROSConnection.GetOrCreateInstance().Subscribe<RosGeometry.PointMsg>(topicName, OnAttractorPositionReceived);

        // 如果没有指定轮椅Transform，尝试自动找到
        if (wheelchairTransform == null)
        {
            GameObject wheelchair = GameObject.Find("wheelchair");
            if (wheelchair == null)
                wheelchair = GameObject.Find("Wheelchair");
            if (wheelchair == null)
                wheelchair = GameObject.Find("wheelchair_pivot");
            
            if (wheelchair != null)
            {
                wheelchairTransform = wheelchair.transform;
            }
        }
        
        // 创建或查找吸引子对象
        Transform existingSphere = transform.Find("AttractorSphere");
        if (existingSphere != null)
        {
            attractorObject = existingSphere.gameObject;
        }
        else if (wheelchairTransform != null)
        {
            existingSphere = wheelchairTransform.Find("AttractorSphere");
            if (existingSphere != null)
            {
                attractorObject = existingSphere.gameObject;
            }
        }
        
        // 如果还是没找到，创建一个简单的球体
        if (attractorObject == null)
        {
            attractorObject = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            attractorObject.name = "AttractorSphere";
            attractorObject.transform.SetParent(wheelchairTransform);
            attractorObject.transform.localScale = Vector3.one * 0.3f;
            attractorObject.transform.localPosition = Vector3.zero;
        }

        // 确保吸引子不会产生物理冲突
        Collider attractorCollider = attractorObject.GetComponent<Collider>();
        if (attractorCollider != null)
        {
            attractorCollider.isTrigger = true;
        }
        
        // 确保吸引子没有Rigidbody，避免物理干扰
        Rigidbody attractorRb = attractorObject.GetComponent<Rigidbody>();
        if (attractorRb != null)
        {
            DestroyImmediate(attractorRb);
        }

        // 记录原始缩放
        originalScale = attractorObject.transform.localScale;
        
        // 初始时隐藏吸引子
        attractorObject.SetActive(false);
        isAttractorActive = false;
    }

    void OnAttractorPositionReceived(RosGeometry.PointMsg attractorPos)
    {
        // 检查是否为无效位置（使用无穷大表示隐藏）
        if (double.IsInfinity(attractorPos.x) || double.IsInfinity(attractorPos.y))
        {
            if (attractorObject != null)
            {
                attractorObject.SetActive(false);
                isAttractorActive = false;
            }
            return;
        }

        // 转换ROS坐标到Unity相对坐标系
        // ROS: x前，y左，z上
        // Unity: x右，y上，z前
        relativeAttractorPos = new Vector3(
            (float)attractorPos.y,       // ROS的y（左）-> Unity的x（右）
            0.5f,                        // 固定高度，便于观察
            (float)attractorPos.x        // ROS的x（前）-> Unity的z（前）
        );

        // 应用可视化缩放
        relativeAttractorPos *= visualScale;

        // 更新吸引子显示状态
        if (attractorObject != null)
        {
            attractorObject.SetActive(true);
            isAttractorActive = true;
        }
    }

    void Update()
    {
        // 更新吸引子的相对位置（现在是轮椅的子物体）
        if (isAttractorActive && attractorObject != null)
        {
            // 直接设置相对于轮椅的本地位置
            attractorObject.transform.localPosition = relativeAttractorPos;
        }

        // 脉冲动画
        if (enablePulseAnimation && isAttractorActive && attractorObject != null)
        {
            float pulseValue = 1.0f + Mathf.Sin(Time.time * pulseSpeed) * pulseScale;
            attractorObject.transform.localScale = originalScale * pulseValue;
        }

        // 可选：旋转动画（相对于自身）
        if (isAttractorActive && attractorObject != null)
        {
            attractorObject.transform.Rotate(0, 30f * Time.deltaTime, 0, Space.Self);
        }
    }

    void OnDestroy()
    {
        // 取消ROS订阅
        if (ROSConnection.GetOrCreateInstance() != null)
        {
            ROSConnection.GetOrCreateInstance().Unsubscribe(topicName);
        }
    }
}