using UnityEngine;
using Unity.Robotics.ROSTCPConnector;
using RosGeometry = RosMessageTypes.Geometry;

public class AttractorVisualizer : MonoBehaviour
{
    [Header("Attractor Visualization Settings")]
    public Transform wheelchairTransform;  // Wheelchair Transform reference
    public float visualScale = 1.0f;       // Visualization scale factor

    private GameObject leftAttractor;    // Left direction attractor (blue)
    private GameObject forwardAttractor; // Forward direction attractor (red)
    private GameObject rightAttractor;   // Right direction attractor (green)
    
    // Public accessors for BCIFeedback use
    public GameObject LeftAttractor => leftAttractor;
    public GameObject ForwardAttractor => forwardAttractor;
    public GameObject RightAttractor => rightAttractor;
    
    private Vector3 originalScale;
    public Vector3 arrowStartPosition = new Vector3(0, 0, 1f); // Arrow start position (relative to wheelchair)

    void Start()
    {
        // Subscribe to three ROS topics
        ROSConnection.GetOrCreateInstance().Subscribe<RosGeometry.PointMsg>("/left_attractor_pos", OnLeftAttractorReceived);
        ROSConnection.GetOrCreateInstance().Subscribe<RosGeometry.PointMsg>("/forward_attractor_pos", OnForwardAttractorReceived);
        ROSConnection.GetOrCreateInstance().Subscribe<RosGeometry.PointMsg>("/right_attractor_pos", OnRightAttractorReceived);

        // Automatically find wheelchair Transform
        if (wheelchairTransform == null)
        {
            GameObject wheelchair = GameObject.Find("wheelchair") ?? GameObject.Find("Wheelchair") ?? GameObject.Find("wheelchair_pivot");
            if (wheelchair != null) wheelchairTransform = wheelchair.transform;
        }

        // Create three attractor arrows
        leftAttractor = CreateAttractorArrow("LeftAttractor", Color.blue);
        forwardAttractor = CreateAttractorArrow("ForwardAttractor", Color.red);
        rightAttractor = CreateAttractorArrow("RightAttractor", Color.green);

        originalScale = Vector3.one * 0.3f;
    }

    GameObject CreateAttractorArrow(string name, Color color)
    {
        // Create empty parent object as arrow container
        GameObject arrowContainer = new GameObject(name);
        arrowContainer.transform.SetParent(wheelchairTransform);
        arrowContainer.transform.localPosition = arrowStartPosition;
        
        // Create arrow body (cylinder - progress bar)
        GameObject shaft = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
        shaft.name = name + "_Shaft";
        shaft.transform.SetParent(arrowContainer.transform);
        shaft.transform.localPosition = Vector3.zero;
        shaft.transform.localRotation = Quaternion.Euler(90, 0, 0); // Rotate 90 degrees to align with Z-axis
        shaft.transform.localScale = new Vector3(0.03f, 0.4f, 0.3f); // Slightly thicker cylinder

        // Set cylinder material transparency
        Renderer shaftRenderer = shaft.GetComponent<Renderer>();
        Shader unlitTransparentShader = Shader.Find("Universal Render Pipeline/Unlit");
        if(unlitTransparentShader == null) 
        {
            unlitTransparentShader = Shader.Find("Unlit/Transparent");
        }

        var shaftMaterial = new Material(unlitTransparentShader);
        shaftMaterial.color = new Color(color.r, color.g, color.b, 0.3f);
        
        // Correctly set URP transparent material properties
        shaftMaterial.SetFloat("_Surface", 1); // Set surface type to transparent
        shaftMaterial.SetFloat("_Blend", 0); // Set blend mode to alpha
        shaftMaterial.SetFloat("_AlphaClip", 0); // Disable alpha clipping
        shaftMaterial.SetFloat("_SrcBlend", (float)UnityEngine.Rendering.BlendMode.SrcAlpha);
        shaftMaterial.SetFloat("_DstBlend", (float)UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha);
        shaftMaterial.SetFloat("_ZWrite", 0); // Disable depth writing
        shaftMaterial.renderQueue = (int)UnityEngine.Rendering.RenderQueue.Transparent;
        
        // Enable keywords
        shaftMaterial.EnableKeyword("_SURFACE_TYPE_TRANSPARENT");
        shaftMaterial.EnableKeyword("_ALPHAPREMULTIPLY_ON");
        
        shaftRenderer.material = shaftMaterial;
        
        // Create arrow head (cone)
        GameObject arrowHead = new GameObject(name + "_Head");
        arrowHead.transform.SetParent(arrowContainer.transform);
        arrowHead.transform.localPosition = new Vector3(0, 0, 0.6f); // Place along Z-axis
        
        // Create cone mesh
        MeshFilter meshFilter = arrowHead.AddComponent<MeshFilter>();
        MeshRenderer meshRenderer = arrowHead.AddComponent<MeshRenderer>();
        Mesh coneMesh = new Mesh();

        int segments = 16; // Number of segments for cone base
        float radius = 0.7f; // Base radius
        float height = 1.1f; // Cone height
        
        Vector3[] vertices = new Vector3[segments + 2]; // Base vertices + apex + base center
        int[] triangles = new int[segments * 6]; // Base triangles + side triangles
        
        // Vertices
        vertices[0] = new Vector3(0, 0, height); // Cone apex
        vertices[1] = new Vector3(0, 0, -0.2f); // Base center
        
        // Base vertices
        for (int i = 0; i < segments; i++)
        {
            float angle = i * 2 * Mathf.PI / segments;
            vertices[i + 2] = new Vector3(Mathf.Cos(angle) * radius, Mathf.Sin(angle) * radius, 0);
        }
        
        int triIndex = 0;
        // Side triangles
        for (int i = 0; i < segments; i++)
        {
            int next = (i + 1) % segments;
            triangles[triIndex] = 0; // Apex
            triangles[triIndex + 1] = i + 2;
            triangles[triIndex + 2] = next + 2;
            triIndex += 3;
        }
        // Base triangles
        for (int i = 0; i < segments; i++)
        {
            int next = (i + 1) % segments;
            triangles[triIndex] = 1; // Base center
            triangles[triIndex + 1] = next + 2;
            triangles[triIndex + 2] = i + 2;
            triIndex += 3;
        }
        
        coneMesh.vertices = vertices;
        coneMesh.triangles = triangles;
        coneMesh.RecalculateNormals();
        meshFilter.mesh = coneMesh;
        
        // Set cone material (opaque)
        Material headMaterial = new Material(Shader.Find("Universal Render Pipeline/Lit"));
        headMaterial.color = color;
        meshRenderer.material = headMaterial;
        
        // Apply material to all child components and remove physics components
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

        // Check for invalid positions
        if (double.IsInfinity(pos.x) || double.IsInfinity(pos.y))
        {
            attractor.SetActive(false);
            return;
        }

        // Calculate target position (coordinate conversion completed on ROS side)
        Vector3 targetPos = new Vector3((float)pos.x, (float)pos.y, (float)pos.z) * visualScale;
        
        // Set arrow start position
        attractor.transform.localPosition = arrowStartPosition;
        
        // Calculate direction and distance from start position to target position
        Vector3 direction = targetPos - arrowStartPosition;
        float distance = direction.magnitude;
        
        if (distance > 0.01f) // Avoid division by zero error
        {
            // Calculate arrow pointing direction (using Z-axis as forward direction)
            attractor.transform.localRotation = Quaternion.LookRotation(direction.normalized, Vector3.up);
            
            // Adjust arrow length to match distance
            Transform shaft = attractor.transform.Find(attractor.name + "_Shaft");
            Transform head = attractor.transform.Find(attractor.name + "_Head");
            
            if (shaft != null)
            {
                float shaftLength = distance;
                shaft.localScale = new Vector3(0.03f, shaftLength * 0.5f, 0.03f);
                shaft.localPosition = new Vector3(0, 0, shaftLength * 0.5f); // Position along Z-axis
            }
            
            if (head != null)
            {
                // Adjust arrow head position to arrow end (Z-axis)
                head.localPosition = new Vector3(0, 0, distance);
                // Adjust head size based on distance
                float headScale = Mathf.Clamp(distance * 0.1f, 0.05f, 0.2f);
                head.localScale = new Vector3(headScale, headScale, headScale * 1.5f); // Z-axis stretch
            }
                        
            attractor.SetActive(true);
        }
        else
        {
            attractor.SetActive(false);
        }
    }

}