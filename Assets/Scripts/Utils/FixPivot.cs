using UnityEngine;

[ExecuteInEditMode]
public class FixPivot : MonoBehaviour
{
    public Vector3 pivotOffset;  // 想要的 pivot 偏移
    public Vector3 pivotRotation; // 想要的旋转修正（度数）

    void Start()
    {
        // 新建一个空父物体作为新的 pivot
        GameObject pivotGO = new GameObject(name + "_Pivot");
        pivotGO.transform.position = transform.position;
        pivotGO.transform.rotation = transform.rotation;

        // 把原模型放到 pivot 下
        transform.SetParent(pivotGO.transform);

        // 调整模型相对于 pivot 的位置和旋转
        transform.localPosition = pivotOffset;
        transform.localRotation = Quaternion.Euler(pivotRotation);

        // 如果需要在运行时访问新 pivot，可以存下来
        // 例如：this.newPivot = pivotGO.transform;
    }
}
