using UnityEngine;

namespace Simulator.Utils
{
    public static class NoiseUtils
    {
        // Box-Muller方法生成标准高斯分布（均值0，方差1）
        public static float GenerateGaussianNoise()
        {
            float u1 = 1.0f - Random.value;
            float u2 = 1.0f - Random.value;
            return Mathf.Sqrt(-2.0f * Mathf.Log(u1)) * Mathf.Cos(2.0f * Mathf.PI * u2);
        }
    }
}
