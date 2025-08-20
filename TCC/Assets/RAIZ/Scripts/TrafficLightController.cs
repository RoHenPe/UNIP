using UnityEngine;

public class TrafficLightController : MonoBehaviour
{
    public GameObject redLight;
    public GameObject yellowLight;
    public GameObject greenLight;

    public enum LightState { Red, Yellow, Green };
    private LightState currentState = LightState.Red;

    // Propriedades para armazenar a demanda de tráfego.
    // O CentralCoordinator irá preenchê-las.
    public float DemandNS { get; private set; } // Demanda Norte-Sul
    public float DemandEW { get; private set; } // Demanda Leste-Oeste

    // Tempo de ajuste para coordenação
    private float coordinationBias = 0f;

    void Start()
    {
        // Define o estado inicial como Vermelho
        SetState(LightState.Red);
    }

    // Métodos para mudar o estado das luzes
    public void SetState(LightState newState)
    {
        currentState = newState;
        UpdateVisuals();
    }

    private void UpdateVisuals()
    {
        switch (currentState)
        {
            case LightState.Red:
                redLight.SetActive(true);
                yellowLight.SetActive(false);
                greenLight.SetActive(false);
                break;
            case LightState.Yellow:
                redLight.SetActive(false);
                yellowLight.SetActive(true);
                greenLight.SetActive(false);
                break;
            case LightState.Green:
                redLight.SetActive(false);
                yellowLight.SetActive(false);
                greenLight.SetActive(true);
                break;
        }
    }

    // Método que será chamado pelo CentralCoordinator para atualizar a demanda
    public void UpdateDemand(float demandNS, float demandEW)
    {
        DemandNS = demandNS;
        DemandEW = demandEW;
    }

    // Método para aplicar o ajuste de coordenação
    public void ApplyCoordinationBias(float bias)
    {
        coordinationBias = bias;
    }
}