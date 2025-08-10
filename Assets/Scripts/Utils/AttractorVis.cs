using UnityEngine;
using Unity.Robotics.ROSTCPConnector;
using RosGeometry = RosMessageTypes.Geometry;

public class AttractorVisualizer : MonoBehaviour
{
    [Header("Attractor Visualization Settings")]
    public Transform wheelchairTransform;  // 轮椅的Transform引用
    public float visualScale = 1.0f;       // 可视化缩放系数

    [Header("Animation Settings")]
    public bool enablePulseAnimation = true;     // 启用脉冲动画
    public float pulseSpeed = 2.0f;             // 脉冲速度
    public float pulseScale = 0.2f;             // 脉冲幅度

    private GameObject leftAttractor;    // 左方向吸引子（蓝色）
    private GameObject forwardAttractor; // 前方向吸引子（红色）
    private GameObject rightAttractor;   // 右方向吸引子（绿色）
    
    private Vector3 originalScale;

    void Start()
    {
        // 订阅三个ROS话题
        ROSConnection.GetOrCreateInstance().Subscribe<RosGeometry.PointMsg>("/left_attractor_pos", OnLeftAttractorReceived);
        ROSConnection.GetOrCreateInstance().Subscribe<RosGeometry.PointMsg>("/forward_attractor_pos", OnForwardAttractorReceived);
        ROSConnection.GetOrCreateInstance().Subscribe<RosGeometry.PointMsg>("/right_attractor_pos", OnRightAttractorReceived);

        // 自动找到轮椅Transform
        if (wheelchairTransform == null)
        {
            GameObject wheelchair = GameObject.Find("wheelchair") ?? GameObject.Find("Wheelchair") ?? GameObject.Find("wheelchair_pivot");
            if (wheelchair != null) wheelchairTransform = wheelchair.transform;
        }

        // 创建三个吸引子球体
        leftAttractor = CreateAttractorSphere("LeftAttractor", Color.blue);
        forwardAttractor = CreateAttractorSphere("ForwardAttractor", Color.red);
        rightAttractor = CreateAttractorSphere("RightAttractor", Color.green);

        originalScale = Vector3.one * 0.3f;
    }

    GameObject CreateAttractorSphere(string name, Color color)
    {
        GameObject sphere = GameObject.CreatePrimitive(PrimitiveType.Sphere);
        sphere.name = name;
        sphere.transform.SetParent(wheelchairTransform);
        sphere.transform.localScale = originalScale;
        sphere.transform.localPosition = Vector3.zero;
        
        // 设置颜色
        Renderer renderer = sphere.GetComponent<Renderer>();
        if (renderer != null)
        {
            renderer.material = new Material(Shader.Find("Universal Render Pipeline/Lit"));
            renderer.material.color = color;
            renderer.material.SetFloat("_Mode", 3); // 透明模式
            renderer.material.SetFloat("_Metallic", 0.5f);
            renderer.material.SetFloat("_Glossiness", 0.8f);
        }
        
        // 移除物理组件
        if (sphere.GetComponent<Collider>()) DestroyImmediate(sphere.GetComponent<Collider>());
        if (sphere.GetComponent<Rigidbody>()) DestroyImmediate(sphere.GetComponent<Rigidbody>());
        
        sphere.SetActive(false);
        return sphere;
    }

    void OnLeftAttractorReceived(RosGeometry.PointMsg pos)
    {
        UpdateAttractor(leftAttractor, pos);
    }

    void OnForwardAttractorReceived(RosGeometry.PointMsg pos)
    {
        UpdateAttractor(forwardAttractor, pos);
    }

    void OnRightAttractorReceived(RosGeometry.PointMsg pos)
    {
        UpdateAttractor(rightAttractor, pos);
    }

    void UpdateAttractor(GameObject attractor, RosGeometry.PointMsg pos)
    {
        if (attractor == null) return;

        // 检查无效位置
        if (double.IsInfinity(pos.x) || double.IsInfinity(pos.y))
        {
            attractor.SetActive(false);
            return;
        }

        // 设置位置（ROS端已完成坐标转换）
        Vector3 localPos = new Vector3((float)pos.x, (float)pos.y, (float)pos.z) * visualScale;
        attractor.transform.localPosition = localPos;
        attractor.SetActive(true);
    }

    void Update()
    {
        // 脉冲动画
        if (enablePulseAnimation)
        {
            float pulseValue = 1.0f + Mathf.Sin(Time.time * pulseSpeed) * pulseScale;
            Vector3 newScale = originalScale * pulseValue;
            
            if (leftAttractor.activeInHierarchy) leftAttractor.transform.localScale = newScale;
            if (forwardAttractor.activeInHierarchy) forwardAttractor.transform.localScale = newScale;
            if (rightAttractor.activeInHierarchy) rightAttractor.transform.localScale = newScale;
        }

        // 旋转动画
        float rotSpeed = 30f * Time.deltaTime;
        if (leftAttractor.activeInHierarchy) leftAttractor.transform.Rotate(0, rotSpeed, 0, Space.Self);
        if (forwardAttractor.activeInHierarchy) forwardAttractor.transform.Rotate(0, rotSpeed, 0, Space.Self);
        if (rightAttractor.activeInHierarchy) rightAttractor.transform.Rotate(0, rotSpeed, 0, Space.Self);
    }
}