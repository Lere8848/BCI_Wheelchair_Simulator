using UnityEngine;
using UnityEditor;

public class Standard2URPLit : AssetPostprocessor
{
    void OnPostprocessMaterial(Material material)
    {
        if (material.shader.name == "Standard")
        {
            var tex = material.HasProperty("_MainTex") ? material.GetTexture("_MainTex") : null;

            Debug.Log($"[URP Auto Convert] {material.name} → URP/Lit");

            // 替换 Shader
            material.shader = Shader.Find("Universal Render Pipeline/Lit");

            // 推迟执行：确保 Shader 切换后再设置 BaseMap
            EditorApplication.delayCall += () =>
            {
                if (material != null && tex != null && material.HasProperty("_BaseMap"))
                {
                    material.SetTexture("_BaseMap", tex);
                    EditorUtility.SetDirty(material);
                    AssetDatabase.SaveAssets();
                    Debug.Log($"[URP Auto Set] {material.name} BaseMap set to {tex.name}");
                }
            };
        }
    }
}
