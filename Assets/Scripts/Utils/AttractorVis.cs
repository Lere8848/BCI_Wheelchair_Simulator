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
    private Vector3 arrowStartPosition = new Vector3(0, 0, 0.4f); // 箭头起始位置（相对于轮椅）

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

        // 创建三个吸引子箭头
        leftAttractor = CreateAttractorArrow("LeftAttractor", Color.blue);
        forwardAttractor = CreateAttractorArrow("ForwardAttractor", Color.red);
        rightAttractor = CreateAttractorArrow("RightAttractor", Color.green);

        originalScale = Vector3.one * 0.3f;
    }

    GameObject CreateAttractorArrow(string name, Color color)
    {
        // 创建空的父物体作为箭头容器
        GameObject arrowContainer = new GameObject(name);
        arrowContainer.transform.SetParent(wheelchairTransform);
        arrowContainer.transform.localPosition = arrowStartPosition;
        
        // 创建箭头主体（圆柱体 - 箭杆）
        GameObject shaft = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
        shaft.name = name + "_Shaft";
        shaft.transform.SetParent(arrowContainer.transform);
        shaft.transform.localPosition = Vector3.zero;
        shaft.transform.localRotation = Quaternion.Euler(90, 0, 0); // 旋转90度使其沿Z轴
        shaft.transform.localScale = new Vector3(0.03f, 0.5f, 0.03f); // 稍微粗一些的圆柱体
        
        // 创建箭头头部（圆锥体形状 - 使用拉伸的球体模拟）
        GameObject arrowHead = GameObject.CreatePrimitive(PrimitiveType.Sphere);
        arrowHead.name = name + "_Head";
        arrowHead.transform.SetParent(arrowContainer.transform);
        arrowHead.transform.localPosition = new Vector3(0, 0, 1.0f); // 沿Z轴放置
        arrowHead.transform.localScale = new Vector3(0.1f, 0.1f, 0.15f); // Z轴拉伸成锥形
        
        // 创建箭头尾翼（3个小的立方体）
        for (int i = 0; i < 3; i++)
        {
            GameObject feather = GameObject.CreatePrimitive(PrimitiveType.Cube);
            feather.name = name + "_Feather" + i;
            feather.transform.SetParent(arrowContainer.transform);
            
            // 计算尾翼位置和旋转
            float angle = i * 120f; // 每120度放置一个尾翼
            Vector3 offset = new Vector3(
                Mathf.Sin(angle * Mathf.Deg2Rad) * 0.04f,
                Mathf.Cos(angle * Mathf.Deg2Rad) * 0.04f,
                -0.8f // 箭杆后端（Z轴负方向）
            );
            
            feather.transform.localPosition = offset;
            feather.transform.localScale = new Vector3(0.02f, 0.006f, 0.1f); // 调整为Z轴方向的薄片
            feather.transform.localRotation = Quaternion.Euler(0, 0, angle);
        }
        
        // 设置材质和颜色
        Material arrowMaterial = new Material(Shader.Find("Universal Render Pipeline/Lit"));
        arrowMaterial.color = color;
        arrowMaterial.SetFloat("_Metallic", 0.3f);
        arrowMaterial.SetFloat("_Smoothness", 0.8f);
        
        // 为所有子组件应用材质并移除物理组件
        Component[] renderers = arrowContainer.GetComponentsInChildren<Renderer>();
        Component[] colliders = arrowContainer.GetComponentsInChildren<Collider>();
        Component[] rigidbodies = arrowContainer.GetComponentsInChildren<Rigidbody>();
        
        foreach (Renderer renderer in renderers)
        {
            if (renderer != null) renderer.material = arrowMaterial;
        }
        
        foreach (Collider collider in colliders)
        {
            if (collider != null) DestroyImmediate(collider);
        }
        
        foreach (Rigidbody rb in rigidbodies)
        {
            if (rb != null) DestroyImmediate(rb);
        }
        
        arrowContainer.SetActive(false);
        return arrowContainer;
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

        // 计算目标位置（ROS端已完成坐标转换）
        Vector3 targetPos = new Vector3((float)pos.x, (float)pos.y, (float)pos.z) * visualScale;
        
        // 设置箭头起始位置
        attractor.transform.localPosition = arrowStartPosition;
        
        // 计算从起始位置到目标位置的方向和距离
        Vector3 direction = targetPos - arrowStartPosition;
        float distance = direction.magnitude;
        
        if (distance > 0.01f) // 避免除零错误
        {
            // 计算箭头应该指向的方向（使用Z轴作为前进方向）
            attractor.transform.localRotation = Quaternion.LookRotation(direction.normalized, Vector3.up);
            
            // 调整箭头长度以匹配距离
            Transform shaft = attractor.transform.Find(attractor.name + "_Shaft");
            Transform head = attractor.transform.Find(attractor.name + "_Head");
            
            if (shaft != null)
            {
                // 调整圆柱体长度，使其占箭头总长度的80%
                float shaftLength = distance * 0.8f;
                shaft.localScale = new Vector3(0.03f, shaftLength * 0.5f, 0.03f);
                shaft.localPosition = new Vector3(0, 0, shaftLength * 0.5f); // 沿Z轴定位
            }
            
            if (head != null)
            {
                // 调整箭头头部位置到箭头末端（Z轴）
                head.localPosition = new Vector3(0, 0, distance);
                // 根据距离调整头部大小
                float headScale = Mathf.Clamp(distance * 0.1f, 0.05f, 0.2f);
                head.localScale = new Vector3(headScale, headScale, headScale * 1.5f); // Z轴拉伸
            }
            
            // 调整尾翼位置
            for (int i = 0; i < 3; i++)
            {
                Transform feather = attractor.transform.Find(attractor.name + "_Feather" + i);
                if (feather != null)
                {
                    float angle = i * 120f;
                    Vector3 offset = new Vector3(
                        Mathf.Sin(angle * Mathf.Deg2Rad) * 0.04f,
                        Mathf.Cos(angle * Mathf.Deg2Rad) * 0.04f,
                        -distance * 0.1f // 尾翼位置相对于箭头长度（Z轴负方向）
                    );
                    feather.localPosition = offset;
                }
            }
            
            attractor.SetActive(true);
        }
        else
        {
            attractor.SetActive(false);
        }
    }

    // void Update()
    // {
        // 脉冲动画 - 已注释掉，会导致箭头不自然
        // if (enablePulseAnimation)
        // {
        //     float pulseValue = 1.0f + Mathf.Sin(Time.time * pulseSpeed) * pulseScale;
        //     
        //     ApplyPulseToArrow(leftAttractor, pulseValue);
        //     ApplyPulseToArrow(forwardAttractor, pulseValue);
        //     ApplyPulseToArrow(rightAttractor, pulseValue);
        // }

        // 旋转动画（绕自身Z轴旋转）
        // float rotSpeed = 30f * Time.deltaTime;
        // if (leftAttractor.activeInHierarchy) leftAttractor.transform.Rotate(0, 0, rotSpeed, Space.Self);
        // if (forwardAttractor.activeInHierarchy) forwardAttractor.transform.Rotate(0, 0, rotSpeed, Space.Self);
        // if (rightAttractor.activeInHierarchy) rightAttractor.transform.Rotate(0, 0, rotSpeed, Space.Self);
    // }

    // 脉冲动画方法 - 已注释掉
    // void ApplyPulseToArrow(GameObject arrow, float pulseValue)
    // {
    //     if (arrow == null || !arrow.activeInHierarchy) return;
    //     
    //     Transform shaft = arrow.transform.Find(arrow.name + "_Shaft");
    //     Transform head = arrow.transform.Find(arrow.name + "_Head");
    //     
    //     // 对箭杆应用脉冲（主要是径向缩放）
    //     if (shaft != null)
    //     {
    //         Vector3 baseScale = new Vector3(0.03f, shaft.localScale.y, 0.03f);
    //         shaft.localScale = new Vector3(baseScale.x * pulseValue, baseScale.y, baseScale.z * pulseValue);
    //     }
    //     
    //     // 对箭头头部应用脉冲
    //     if (head != null)
    //     {
    //         Vector3 currentScale = head.localScale;
    //         Vector3 baseScale = new Vector3(currentScale.x / pulseValue, currentScale.y / pulseValue, currentScale.z / pulseValue);
    //         head.localScale = baseScale * pulseValue;
    //     }
    //     
    //     // 对尾翼应用脉冲
    //     for (int i = 0; i < 3; i++)
    //     {
    //         Transform feather = arrow.transform.Find(arrow.name + "_Feather" + i);
    //         if (feather != null)
    //         {
    //             Vector3 baseScale = new Vector3(0.02f, 0.1f, 0.006f);
    //             feather.localScale = baseScale * pulseValue;
    //         }
    //     }
    // }
}