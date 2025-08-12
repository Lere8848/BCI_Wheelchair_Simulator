using UnityEngine;
using Unity.Robotics.ROSTCPConnector;
using RosGeometry = RosMessageTypes.Geometry;

public class AttractorVisualizer : MonoBehaviour
{
    [Header("Attractor Visualization Settings")]
    public Transform wheelchairTransform;  // 轮椅的Transform引用
    public float visualScale = 1.0f;       // 可视化缩放系数

    private GameObject leftAttractor;    // 左方向吸引子（蓝色）
    private GameObject forwardAttractor; // 前方向吸引子（红色）
    private GameObject rightAttractor;   // 右方向吸引子（绿色）
    
    // 公共访问器，供BCIFeedback使用
    public GameObject LeftAttractor => leftAttractor;
    public GameObject ForwardAttractor => forwardAttractor;
    public GameObject RightAttractor => rightAttractor;
    
    private Vector3 originalScale;
    public Vector3 arrowStartPosition = new Vector3(0, 0, 1f); // 箭头起始位置（相对于轮椅）

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
        
        // 创建箭头主体（圆柱体 - 进度条）
        GameObject shaft = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
        shaft.name = name + "_Shaft";
        shaft.transform.SetParent(arrowContainer.transform);
        shaft.transform.localPosition = Vector3.zero;
        shaft.transform.localRotation = Quaternion.Euler(90, 0, 0); // 旋转90度使其沿Z轴
        shaft.transform.localScale = new Vector3(0.03f, 0.4f, 0.3f); // 稍微粗一些的圆柱体

        // 设置圆柱体材质的透明度
        Renderer shaftRenderer = shaft.GetComponent<Renderer>();
        Shader unlitTransparentShader = Shader.Find("Universal Render Pipeline/Unlit");
        if(unlitTransparentShader == null) 
        {
            unlitTransparentShader = Shader.Find("Unlit/Transparent");
        }

        var shaftMaterial = new Material(unlitTransparentShader);
        shaftMaterial.color = new Color(color.r, color.g, color.b, 0.3f);
        
        // 正确设置URP透明材质属性
        shaftMaterial.SetFloat("_Surface", 1); // 设置surface type为transparent
        shaftMaterial.SetFloat("_Blend", 0); // 设置blend mode为alpha
        shaftMaterial.SetFloat("_AlphaClip", 0); // 禁用alpha clipping
        shaftMaterial.SetFloat("_SrcBlend", (float)UnityEngine.Rendering.BlendMode.SrcAlpha);
        shaftMaterial.SetFloat("_DstBlend", (float)UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha);
        shaftMaterial.SetFloat("_ZWrite", 0); // 禁用深度写入
        shaftMaterial.renderQueue = (int)UnityEngine.Rendering.RenderQueue.Transparent;
        
        // 启用关键字
        shaftMaterial.EnableKeyword("_SURFACE_TYPE_TRANSPARENT");
        shaftMaterial.EnableKeyword("_ALPHAPREMULTIPLY_ON");
        
        shaftRenderer.material = shaftMaterial;
        
        // 创建箭头头部（圆锥体）
        GameObject arrowHead = new GameObject(name + "_Head");
        arrowHead.transform.SetParent(arrowContainer.transform);
        arrowHead.transform.localPosition = new Vector3(0, 0, 0.6f); // 沿Z轴放置
        
        // 创建圆锥体mesh
        MeshFilter meshFilter = arrowHead.AddComponent<MeshFilter>();
        MeshRenderer meshRenderer = arrowHead.AddComponent<MeshRenderer>();
        Mesh coneMesh = new Mesh();

        int segments = 16; // 圆锥底面的分段数
        float radius = 0.7f; // 底面半径
        float height = 1.1f; // 圆锥高度
        
        Vector3[] vertices = new Vector3[segments + 2]; // 底面顶点 + 顶点 + 底面中心
        int[] triangles = new int[segments * 6]; // 底面三角形 + 侧面三角形
        
        // 顶点
        vertices[0] = new Vector3(0, 0, height); // 圆锥顶点
        vertices[1] = new Vector3(0, 0, -0.2f); // 底面中心
        
        // 底面顶点
        for (int i = 0; i < segments; i++)
        {
            float angle = i * 2 * Mathf.PI / segments;
            vertices[i + 2] = new Vector3(Mathf.Cos(angle) * radius, Mathf.Sin(angle) * radius, 0);
        }
        
        int triIndex = 0;
        // 侧面三角形
        for (int i = 0; i < segments; i++)
        {
            int next = (i + 1) % segments;
            triangles[triIndex] = 0; // 顶点
            triangles[triIndex + 1] = i + 2;
            triangles[triIndex + 2] = next + 2;
            triIndex += 3;
        }
        // 底面三角形
        for (int i = 0; i < segments; i++)
        {
            int next = (i + 1) % segments;
            triangles[triIndex] = 1; // 底面中心
            triangles[triIndex + 1] = next + 2;
            triangles[triIndex + 2] = i + 2;
            triIndex += 3;
        }
        
        coneMesh.vertices = vertices;
        coneMesh.triangles = triangles;
        coneMesh.RecalculateNormals();
        meshFilter.mesh = coneMesh;
        
        // 设置圆锥体的材质(不透明)
        Material headMaterial = new Material(Shader.Find("Universal Render Pipeline/Lit"));
        headMaterial.color = color;
        meshRenderer.material = headMaterial;
        
        // 为所有子组件应用材质并移除物理组件
        // Component[] renderers = arrowContainer.GetComponentsInChildren<Renderer>();
        Component[] colliders = arrowContainer.GetComponentsInChildren<Collider>();
        Component[] rigidbodies = arrowContainer.GetComponentsInChildren<Rigidbody>();
        
        // foreach (Renderer renderer in renderers){if (renderer != null) renderer.material = headMaterial;}
        foreach (Collider collider in colliders){if (collider != null) DestroyImmediate(collider);}
        foreach (Rigidbody rb in rigidbodies){if (rb != null) DestroyImmediate(rb);}

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
                float shaftLength = distance;
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
                        
            attractor.SetActive(true);
        }
        else
        {
            attractor.SetActive(false);
        }
    }

}