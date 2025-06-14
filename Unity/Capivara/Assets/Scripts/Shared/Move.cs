using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class Move00 : MonoBehaviour
{
    public bool isPaused = false; // Variável para controlar o estado do movimento

    [SerializeField] float speed = -2f;
    [SerializeField] float leftBord;

    // Start is called before the first frame update
    void Start()
    {
        leftBord = Camera.main.ScreenToWorldPoint(Vector3.zero).x;
    }

    // Update is called once per frame
    void Update()
    {
        // Verifica se o movimento está pausado antes de mover o objeto
        if (!isPaused)
        {
            transform.position += new Vector3(speed * Time.deltaTime, 0, 0);

            if (transform.position.x <= -14.99)
            {
                Destroy(gameObject);
            }
        }
    }

    // Método para pausar o movimento
    public void Pause()
    {
        isPaused = true;
    }

    // Método para retomar o movimento
    public void Resume()
    {
        isPaused = false;
    }
}
