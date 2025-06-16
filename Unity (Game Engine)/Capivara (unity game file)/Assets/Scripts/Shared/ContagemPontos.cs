using UnityEngine;

public class Capivara01 : MonoBehaviour
{
    public int score = 0;

    void OnTriggerEnter(Collider other)
    {
        if (other.gameObject.tag == "Barril")
        {
            score++;
            Debug.Log("Score: " + score);
        }
    }
}
