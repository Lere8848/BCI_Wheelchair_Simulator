using UnityEngine;

[ExecuteInEditMode]
public class FixPivot : MonoBehaviour
{
    public Vector3 pivotOffset;  // Desired pivot offset
    public Vector3 pivotRotation; // Desired rotation correction (degrees)

    void Start()
    {
        // Create a new empty parent object as the new pivot
        GameObject pivotGO = new GameObject(name + "_Pivot");
        pivotGO.transform.position = transform.position;
        pivotGO.transform.rotation = transform.rotation;

        // Put the original model under the pivot
        transform.SetParent(pivotGO.transform);

        // Adjust model's position and rotation relative to pivot
        transform.localPosition = pivotOffset;
        transform.localRotation = Quaternion.Euler(pivotRotation);

        // If you need to access the new pivot at runtime, you can store it
        // For example: this.newPivot = pivotGO.transform;
    }
}
