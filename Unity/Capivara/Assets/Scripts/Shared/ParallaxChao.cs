using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class ParallaxChao : MonoBehaviour
{
    private MeshRenderer meshRenderer;
    [SerializeField] float speedTexture;

    // Start is called before the first frame update
    void Start()
    {
        meshRenderer = GetComponent<MeshRenderer>();
    }

    // Update is called once per frame
    void Update()
    {
        meshRenderer.material.mainTextureOffset -= new Vector2(speedTexture * Time.deltaTime, 0);
    }
}
