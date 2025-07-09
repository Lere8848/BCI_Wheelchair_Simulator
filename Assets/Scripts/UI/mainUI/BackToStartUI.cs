using UnityEngine;
using UnityEngine.SceneManagement;

public class BackToStartUI : MonoBehaviour
{
    public void LoadStartupScene()
    {
        SceneManager.LoadScene("StartupScene");
    }
}

