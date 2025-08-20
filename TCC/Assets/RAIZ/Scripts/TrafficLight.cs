using UnityEngine;

public class TrafficLight : MonoBehaviour
{
    public Material redLightMaterial;
    public Material yellowLightMaterial;
    public Material greenLightMaterial;
    public Material offLightMaterial; // Material cinza para a luz apagada

    public Renderer redLightRenderer;
    public Renderer yellowLightRenderer;
    public Renderer greenLightRenderer;

    public enum LightState { Red, Yellow, Green }
    public LightState currentState;

    void Start()
    {
        // Inicia com o semáforo vermelho
        SetLightState(LightState.Red);
    }

    public void SetLightState(LightState newState)
    {
        currentState = newState;

        // Reseta todas as luzes para o estado "apagado"
        redLightRenderer.material = offLightMaterial;
        yellowLightRenderer.material = offLightMaterial;
        greenLightRenderer.material = offLightMaterial;

        // Acende a luz correspondente
        switch (newState)
        {
            case LightState.Red:
                redLightRenderer.material = redLightMaterial;
                break;
            case LightState.Yellow:
                yellowLightRenderer.material = yellowLightMaterial;
                break;
            case LightState.Green:
                greenLightRenderer.material = greenLightMaterial;
                break;
        }
    }
}