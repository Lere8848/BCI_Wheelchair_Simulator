using UnityEngine;
using Unity.Robotics.ROSTCPConnector;
using RosMessageTypes.Geometry;
using RosMessageTypes.Std;

public class BCIFeedback : MonoBehaviour
{
    [Header("BCI Feedback Settings")]
    public AttractorVisualizer attractorVisualizer;

    [Header("Progress Bar Settings")]
    public Color leftColor = new Color(0, 0.5f, 1f, 1f);       // 浅蓝色
    public Color forwardColor = new Color(1f, 0.3f, 0.3f, 1f); // 浅红色
    public Color rightColor = new Color(0.3f, 1f, 0.3f, 1f);   // 浅绿色
    [Range(0.01f, 0.1f)] public float diameterMultiplier = 1.05f;
    [Range(0.001f, 0.1f)] public float minHeight = 0.01f;

    private GameObject leftProgressBar;
    private GameObject forwardProgressBar;
    private GameObject rightProgressBar;

    private float confLeft, confForward, confRight;
    private float threshold = 0.5f;
    private bool isMoving;
    private Vector3 lastWheelchairPosition;
    private bool progressBarsCreated;

    void Start()
    {
        if (attractorVisualizer == null)
        {
            attractorVisualizer = FindFirstObjectByType<AttractorVisualizer>();
            if (attractorVisualizer == null)
            {
                Debug.LogError("AttractorVisualizer not found!");
                return;
            }
        }

        ROSConnection.GetOrCreateInstance().Subscribe<Float32MultiArrayMsg>("/bci_info", OnBCIInfoReceived);
        ROSConnection.GetOrCreateInstance().Subscribe<TwistMsg>("/cmd_vel", OnCmdVelReceived);

        if (attractorVisualizer.wheelchairTransform != null)
        {
            lastWheelchairPosition = attractorVisualizer.wheelchairTransform.position;
        }

        // 立即创建进度条
        CreateProgressBars();
    }

    void CreateProgressBars()
    {
        if (progressBarsCreated) return;

        // 为每个方向创建进度条并指定颜色
        leftProgressBar = CreateProgressBar("LeftProgressBar", attractorVisualizer.LeftAttractor, leftColor);
        forwardProgressBar = CreateProgressBar("ForwardProgressBar", attractorVisualizer.ForwardAttractor, forwardColor);
        rightProgressBar = CreateProgressBar("RightProgressBar", attractorVisualizer.RightAttractor, rightColor);

        progressBarsCreated = true;
        Debug.Log("Progress bars created");
    }

    GameObject CreateProgressBar(string name, GameObject parentAttractor, Color color)
    {
        if (parentAttractor == null)
        {
            Debug.LogWarning($"Parent attractor for {name} not found!");
            return null;
        }

        Transform shaft = parentAttractor.transform.Find(parentAttractor.name + "_Shaft");
        if (shaft == null)
        {
            Debug.LogWarning($"Shaft not found for {parentAttractor.name}");
            return null;
        }

        GameObject progressBar = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
        progressBar.name = name;
        progressBar.transform.SetParent(shaft.parent, false);
        progressBar.transform.localPosition = shaft.localPosition;
        progressBar.transform.localRotation = shaft.localRotation;

        // 使用Unlit材质确保颜色不受光照影响
        Renderer renderer = progressBar.GetComponent<Renderer>();
        Shader unlitShader = Shader.Find("Unlit/Color");
        if (unlitShader == null) unlitShader = Shader.Find("Universal Render Pipeline/Unlit");

        Material progressMaterial = new Material(unlitShader);
        progressMaterial.color = color;
        renderer.material = progressMaterial;

        // 移除碰撞体
        Destroy(progressBar.GetComponent<Collider>());

        // 初始设置为零高度
        Vector3 shaftScale = shaft.localScale;
        progressBar.transform.localScale = new Vector3(
            shaftScale.x * diameterMultiplier + 0.02f,
            minHeight,
            shaftScale.z * diameterMultiplier + 0.02f
        );

        progressBar.transform.localPosition = new Vector3(
        shaft.localPosition.x,
        shaft.localPosition.y,
        shaft.localPosition.z - shaft.localScale.y / 2 + minHeight / 2
        );

        progressBar.SetActive(true);
        Debug.Log($"Created progress bar: {name} under {shaft.parent.name}");

        return progressBar;
    }

    void OnBCIInfoReceived(Float32MultiArrayMsg msg)
    {
        if (msg.data.Length < 7) return;

        // 解析消息
        confLeft = msg.data[0];
        confForward = msg.data[1];
        confRight = msg.data[2];
        threshold = msg.data[6];

        Debug.Log($"Received BCI info: L={confLeft}, F={confForward}, R={confRight}, T={threshold}");

        // 确保进度条已创建
        if (!progressBarsCreated) CreateProgressBars();
    }

    void OnCmdVelReceived(TwistMsg msg)
    {
        // 检查轮椅是否在移动
        bool newMoving = msg.linear.x != 0 || msg.linear.y != 0 || msg.linear.z != 0 ||
                         msg.angular.x != 0 || msg.angular.y != 0 || msg.angular.z != 0;

        if (newMoving != isMoving)
        {
            Debug.Log($"Wheelchair moving state changed: {isMoving} -> {newMoving}");
            isMoving = newMoving;
        }
    }

    void Update()
    {
        if (attractorVisualizer == null) return;

        // 检测轮椅实际移动
        CheckWheelchairMovement();

        // 更新进度条
        UpdateProgressBar(leftProgressBar, confLeft, attractorVisualizer.LeftAttractor);
        UpdateProgressBar(forwardProgressBar, confForward, attractorVisualizer.ForwardAttractor);
        UpdateProgressBar(rightProgressBar, confRight, attractorVisualizer.RightAttractor);
    }

    void CheckWheelchairMovement()
    {
        if (attractorVisualizer.wheelchairTransform == null) return;

        Vector3 currentPosition = attractorVisualizer.wheelchairTransform.position;
        float distance = Vector3.Distance(currentPosition, lastWheelchairPosition);

        if (distance > 0.01f)
        {
            if (!isMoving)
            {
                Debug.Log($"Wheelchair started moving (distance: {distance})");
                isMoving = true;
            }
            lastWheelchairPosition = currentPosition;
        }
        else if (isMoving)
        {
            Debug.Log("Wheelchair stopped");
            isMoving = false;
        }
    }

    void UpdateProgressBar(GameObject progressBar, float confidence, GameObject attractor)
    {
        if (progressBar == null || attractor == null) return;

        CheckWheelchairMovement();

        // 当轮椅移动时，隐藏进度条
        if (!isMoving)
        {

            progressBar.SetActive(true);

            Transform shaft = attractor.transform.Find(attractor.name + "_Shaft");
            if (shaft == null) return;

            // 计算进度比例 (0-1)
            float progress = Mathf.Clamp01(confidence / threshold);

            // 获取原始箭头圆柱体的高度
            float maxHeight = shaft.localScale.y;

            // 更新进度条高度
            Vector3 currentScale = progressBar.transform.localScale;
            float newHeight = Mathf.Lerp(minHeight, maxHeight, progress);

            progressBar.transform.localScale = new Vector3(
                currentScale.x,
                newHeight,
                currentScale.z
            );

            // 保持底部固定位置
            progressBar.transform.localPosition = new Vector3(
                shaft.localPosition.x,
                shaft.localPosition.y,
                shaft.localPosition.z - shaft.localScale.y / 2 + newHeight / 2
            );

            isMoving = false; // 重置移动状态，确保进度条在轮椅停止时更新
            Debug.Log($"Updating {progressBar.name}: conf={confidence}, progress={progress}, height={newHeight}");
        }
    }
}