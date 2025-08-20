using UnityEngine;

public class VehicleAI : MonoBehaviour
{
    public float speed = 10.0f;
    public float raycastDistance = 15.0f;
    private bool canMove = true;
    private Rigidbody rb;
    
    // Propriedade para identificação de tipos de veículos
    public bool isEmergency = false;
    public bool isBus = false;

    void Start()
    {
        rb = GetComponent<Rigidbody>();
    }

    void FixedUpdate()
    {
        CheckForTrafficLight();

        if (canMove)
        {
            // Move o veículo para frente
            rb.MovePosition(transform.position + transform.forward * speed * Time.fixedDeltaTime);
        }
    }

    void CheckForTrafficLight()
    {
        RaycastHit hit;
        // Dispara um raio para frente para detectar objetos
        if (Physics.Raycast(transform.position, transform.forward, out hit, raycastDistance))
        {
            // Tenta obter o componente TrafficLight do objeto atingido
            TrafficLight trafficLight = hit.collider.GetComponentInParent<TrafficLight>();

            if (trafficLight != null)
            {
                // Se o semáforo estiver vermelho ou amarelo, o veículo para.
                if (trafficLight.currentState == TrafficLight.LightState.Red || trafficLight.currentState == TrafficLight.LightState.Yellow)
                {
                    canMove = false;
                }
                else
                {
                    canMove = true;
                }
            }
            else
            {
                canMove = true;
            }
        }
        else
        {
            canMove = true;
        }
    }
}