using UnityEngine;
using Unity.Robotics.ROSTCPConnector;
using RosMessageTypes.Geometry;
using RosMessageTypes.Std;

public class BCIFeedback : MonoBehaviour
{
    [Header("BCI Feedback Settings")]
    public AttractorVisualizer attractorVisualizer;

    [Header("Progress Bar Settings")]
    public Color leftColor = new Color(0, 0.5f, 1f, 1f);       // Light blue
    public Color forwardColor = new Color(1f, 0.3f, 0.3f, 1f); // Light red
    public Color rightColor = new Color(0.3f, 1f, 0.3f, 1f);   // Light green
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

        // Create progress bars immediately
        CreateProgressBars();
    }

    void CreateProgressBars()
    {
        if (progressBarsCreated) return;

        // Create progress bars for each direction with specified colors
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

        // Create parent object to adjust pivot point (fixed at wheelchair end)
        GameObject parentObj = new GameObject(name + "_Parent");
        parentObj.transform.SetParent(shaft.parent, false);
        
        // Calculate wheelchair end position (cylinder bottom)
        Vector3 bottomPosition = shaft.localPosition;
        bottomPosition.z -= shaft.localScale.y / 2; // Adjust to cylinder bottom
        
        parentObj.transform.localPosition = new Vector3(bottomPosition.x, bottomPosition.y, 0);
        parentObj.transform.localRotation = shaft.localRotation;

        // Create actual progress bar cylinder
        GameObject progressBar = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
        progressBar.name = name;
        progressBar.transform.SetParent(parentObj.transform, false);
        
        // Initial position at parent object center (wheelchair end)
        progressBar.transform.localPosition = Vector3.zero;
        progressBar.transform.localRotation = Quaternion.identity;

        // Use Unlit material to ensure color is not affected by lighting
        Renderer renderer = progressBar.GetComponent<Renderer>();
        Shader unlitShader = Shader.Find("Unlit/Color");
        if (unlitShader == null) unlitShader = Shader.Find("Universal Render Pipeline/Unlit");

        Material progressMaterial = new Material(unlitShader);
        progressMaterial.color = color;
        renderer.material = progressMaterial;

        // Remove collider
        Destroy(progressBar.GetComponent<Collider>());

        // Initial setting to zero height
        Vector3 shaftScale = shaft.localScale;
        progressBar.transform.localScale = new Vector3(
            shaftScale.x * diameterMultiplier + 0.02f,
            minHeight,
            shaftScale.z * diameterMultiplier + 0.02f
        );

        progressBar.transform.localPosition = new Vector3(
        shaft.localPosition.x,
        shaft.localPosition.y,
        shaft.localPosition.z
        );

        progressBar.SetActive(true);
        Debug.Log($"Created progress bar: {name} under {shaft.parent.name}");

        return progressBar;
    }

    void OnBCIInfoReceived(Float32MultiArrayMsg msg)
    {
        if (msg.data.Length < 7) return;

        // Parse message
        confLeft = msg.data[0];
        confForward = msg.data[1];
        confRight = msg.data[2];
        threshold = msg.data[6];

        Debug.Log($"Received BCI info: L={confLeft}, F={confForward}, R={confRight}, T={threshold}");

        // Ensure progress bars are created
        if (!progressBarsCreated) CreateProgressBars();
    }

    void OnCmdVelReceived(TwistMsg msg)
    {
        // Check if wheelchair is moving
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

        // Detect actual wheelchair movement
        CheckWheelchairMovement();

        // Update progress bars
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

        // When wheelchair is moving, hide progress bars and return
        if (isMoving)
        {
            if (progressBar.activeSelf)
            {
                progressBar.SetActive(false);
            }
            return;
        }

        // When wheelchair is stationary, show and update progress bars
        if (!progressBar.activeSelf)
        {
            progressBar.SetActive(true);
        }
        
        // Get progress bar's parent object
        Transform parentObj = progressBar.transform.parent;
        if (parentObj == null) return;

        // Reset parent object position back to starting point
        // todo

        Transform shaft = attractor.transform.Find(attractor.name + "_Shaft");
        if (shaft == null) return;

        // Calculate progress ratio (0-1)
        float progress = Mathf.Clamp01(confidence / threshold);

        // Get original arrow cylinder height
        float maxHeight = shaft.localScale.y;

        // Update progress bar height
        float newHeight = Mathf.Lerp(minHeight, maxHeight, progress);

        // Set progress bar height
        Vector3 currentScale = progressBar.transform.localScale;
        progressBar.transform.localScale = new Vector3(
            currentScale.x,
            newHeight,
            currentScale.z
        );
        // Calculate visual offset due to height change
        float heightDelta = (newHeight * 2 - minHeight) / 2;
        
        // Adjust parent object position to keep bottom fixed (wheelchair end)
        parentObj.transform.localPosition = new Vector3(
            parentObj.transform.localPosition.x,
            parentObj.transform.localPosition.y,
            0
        );

        // Move parent object position by the distance caused by new height position change
        parentObj.transform.localPosition += Vector3.forward * heightDelta;
    }
}