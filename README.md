# AzureRM Terraform Provider retrieval-augmented generation (RAG)

This is a RAG building application to retrieve relevant chunks of [AzureRM Terraform Provider codes](https://github.com/hashicorp/terraform-provider-azurerm) for reference purpose during AzureRM Terraform Provider development. Code chunk extraction is achieved using [Go `ast` module](https://pkg.go.dev/go/ast). [Python `sentence-transformers` package](https://huggingface.co/sentence-transformers) is used to generate embeddings. [ChromaDB vector database](https://docs.trychroma.com/docs/overview/introduction) is used to store the embeddings and perform similarity search.

## Installation

The prerequisite software includes [Go](https://go.dev/doc/install) and [Python](https://www.python.org/downloads/). Clone this repository and run the installation script.

```bash
git clone https://github.com/v-yhyeo0202/azurerm-rag
cd azurerm-rag
./install.sh
```

## Application steps

1. Change configurations in `azurerm-rag/chunk-line-extractor/config.yml` according to the field definition below.
    * `path.repository`: Absolute path of this repository.
    * `path.main`: Name of current directory. It should be unnecessary to change this field.
    * `path.data`: Name of directory to store output of code chunk extraction. It should be unnecessary to change this field.

2. Run following commands to extract the chunk of codes from [AzureRM Terraform Provider repository](https://github.com/hashicorp/terraform-provider-azurerm).
    ```bash
    cd azurerm-rag/chunk-line-extractor
    ./chunk-line-extractor
    ```

3. Change configurations in `azurerm-rag/builder/config.yml` according to the field definition below.
    * `path.repository`: Absolute path of this repository.
    * `path.main`: Name of current directory. It should be unnecessary to change this field.
    * `path.data`: Name of directory where code chunk extraction output is stored. This should be same as defined in step 1. It should be unnecessary to change this field.
    * `path.database`: Name of vector database directory. It should be unnecessary to change this field.
    * `model`: Name of embedding model to be used according to `modelInfo` keys.
    * `modelInfo`: Model information where new model can be added.
    * `modelInfo.*.id`: [Hugging Face](https://huggingface.co/models) model ID.
    * `batch`: Batch size of code chunks passed to model when running `python build.py`.
    * `bReset`: Whether to reset vector database when running `python build.py`. This aims to avoid accidental resetting of vector database.
    * `nResult`: Number of result returned when running `python run.py`.

4. Run following commands to build the RAG (it may take a long time depending on machine specification).
    ```bash
    cd ../builder
    source venv-azurerm-rag-builder/bin/activate
    python build.py
    ```

5. After RAG is built, run query application.
    ```bash
    python run.py
    ```

## Types of chunks

When running query application, user is allowed to search from the tables below.

1. Schema: code chunks of schemas are returned.

2. Property: code chunks of properties are returned.

3. Method: code chunks of methods which names containing the following substring (case-insensitive) are returned. The methods are indexed as they are widely used and have consistent pattern which should be referred to during development.
    * `Create`
	* `Update`
	* `Read`
	* `Delete`
	* `CustomizeDiff`
	* `expand`
	* `flatten`
	* `List`
	* `TestAcc`
	* `Exists`

4. Config: code chunks of Terraform configurations specified in `fmt.Sprintf` method are returned.

5. File: whole files are returned.

The query application will return relative file path, start, and end line numbers of the code chunks. The code chunks or files which contains codes that exceed the context window of embedding model are not included in the vector database and thus will not be returned. For table 1 to 4, only the code chunks from files containing suffixes `_resource.go`, `_resource_list.go`, `_data_source.go`, and `_test.go` are included, while `_resource_identity_gen_test.go` are excluded.

