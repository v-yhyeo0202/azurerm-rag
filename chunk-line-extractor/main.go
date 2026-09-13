package main

import (
	"bytes"
	"fmt"
	"log"
	"os"
	"os/exec"
	"strings"

	"go/ast"
	"go/parser"
	"go/token"
	"gopkg.in/yaml.v3"
	"path/filepath"
)

type ConfigModel struct {
	Path map[string]string `yaml:"path"`
}

var mainFunctionPrefixes = []string{
	"Create",
	"Update",
	"Read",
	"Delete",
	"CustomizeDiff",
	"expand",
	"flatten",
	"List",
	"TestAcc",
	"Exists",
}

var includedFileSuffixes = []string{
	"_resource.go",
	"_resource_list.go",
	"_data_source.go",
	"_test.go",
}

var excludedFileSuffixes = []string{
	"_resource_identity_gen_test.go",
}

var configSubstrings = []string{
	"provider \"",
	"resource \"",
	"list \"",
	"data \"",
	"action \"",
	"locals {",
}

func getInspectFunction(fileSet *token.FileSet, chunkLineFile *os.File) func(node ast.Node) bool {
	return func(node ast.Node) bool {
		if compositeLit, ok := node.(*ast.CompositeLit); ok {
			if mapType, ok := compositeLit.Type.(*ast.MapType); ok {
				if keyIdent, ok := mapType.Key.(*ast.Ident); ok && keyIdent.Name == "string" {
					if valueStarExpr, ok := mapType.Value.(*ast.StarExpr); ok {
						if valueSelectorExpr, ok := valueStarExpr.X.(*ast.SelectorExpr); ok {
							if moduleIdent, ok := valueSelectorExpr.X.(*ast.Ident); ok && moduleIdent.Name == "pluginsdk" && valueSelectorExpr.Sel.Name == "Schema" {
								startPosition := fileSet.Position(compositeLit.Pos())
								endPosition := fileSet.Position(compositeLit.End())
								if _, err := fmt.Fprintf(chunkLineFile, "%s,schema,,%d,%d\n", startPosition.Filename, startPosition.Line-1, endPosition.Line); err != nil {
									log.Fatalf("error writing file: %v", err)
								}

								for _, elt := range compositeLit.Elts {
									if keyValueExpr, ok := elt.(*ast.KeyValueExpr); ok {
										startPosition = fileSet.Position(elt.Pos())
										endPosition = fileSet.Position(elt.End())
										if _, err := fmt.Fprintf(chunkLineFile, "%s,property,%s,%d,%d\n", startPosition.Filename, strings.Trim(keyValueExpr.Key.(*ast.BasicLit).Value, "\""), startPosition.Line-1, endPosition.Line); err != nil {
											log.Fatalf("error writing file: %v", err)
										}
									}
								}
							}
						}
					}
				}
			}
		} else if funcDecl, ok := node.(*ast.FuncDecl); ok {
			functionSelected := false

			for _, mainFunctionPrefix := range mainFunctionPrefixes {
				if len(funcDecl.Name.Name) >= len(mainFunctionPrefix) && strings.Contains(strings.ToLower(funcDecl.Name.Name), strings.ToLower(mainFunctionPrefix)) {
					functionSelected = true
					break
				}
			}

			if functionSelected {
				startPosition := fileSet.Position(funcDecl.Pos())
				endPosition := fileSet.Position(funcDecl.Body.End())
				if _, err := fmt.Fprintf(chunkLineFile, "%s,method,%s,%d,%d\n", startPosition.Filename, funcDecl.Name, startPosition.Line-1, endPosition.Line); err != nil {
					log.Fatalf("error writing file: %v", err)
				}
			}
		} else if callExpr, ok := node.(*ast.CallExpr); ok {
			if selectorExpr, ok := callExpr.Fun.(*ast.SelectorExpr); ok {
				if ident, ok := selectorExpr.X.(*ast.Ident); ok && ident.Name == "fmt" && selectorExpr.Sel.Name == "Sprintf" {
					arg := callExpr.Args[0]
					if basicLitArg, ok := arg.(*ast.BasicLit); ok {
						formattedString := basicLitArg.Value
						configSubstringPresent := false

						for _, configSubstring := range configSubstrings {
							if strings.Contains(formattedString, configSubstring) {
								configSubstringPresent = true
							}
						}

						if configSubstringPresent {
							startPosition := fileSet.Position(arg.Pos())
							endPosition := fileSet.Position(arg.End())

							if _, err := fmt.Fprintf(chunkLineFile, "%s,config,,%d,%d\n", startPosition.Filename, startPosition.Line-1, endPosition.Line); err != nil {
								log.Fatalf("error writing file: %v", err)
							}
						}
					}
				}
			}
		}

		return true
	}
}

func main() {
	configFile, err := os.ReadFile("config.yml")
	if err != nil {
		log.Fatalf("error reading file: %v", err)
	}

	var config ConfigModel
	err = yaml.Unmarshal(configFile, &config)
	if err != nil {
		log.Fatalf("error unmarshalling YAML: %v", err)
	}

	dataPath := filepath.Join(config.Path["repository"], config.Path["data"])
	if err := os.MkdirAll(dataPath, os.ModePerm); err != nil {
		log.Fatalf("error creating directory: %v", err)
	}

	chunkLineFile, err := os.Create(filepath.Join(dataPath, "chunkLine.csv"))
	if err != nil {
		log.Fatalf("error creating file: %v", err)
	}
	defer chunkLineFile.Close()
	chunkLineFile.WriteString("path,chunkType,chunkName,startLine,endLine\n")

	azurermPath := filepath.Join(config.Path["repository"], "terraform-provider-azurerm")
	mainServicePath := filepath.Join(azurermPath, "internal", "services")
	serviceDirEntries, err := os.ReadDir(mainServicePath)
	if err != nil {
		log.Fatalf("error reading `DirEntry`: %v", err)
	}

	for _, serviceDirEntry := range serviceDirEntries {
		servicePath := filepath.Join(mainServicePath, serviceDirEntry.Name())
		resourceDirEntries, err := os.ReadDir(servicePath)
		if err != nil {
			log.Fatalf("error reading `DirEntry`: %v", err)
		}

		fmt.Println(servicePath)

		for _, resourceDirEntry := range resourceDirEntries {
			includedSuffixPresent := false
			for _, includedFileSuffix := range includedFileSuffixes {
				if strings.HasSuffix(resourceDirEntry.Name(), includedFileSuffix) {
					includedSuffixPresent = true
					break
				}
			}

			excludedSuffixPresent := false
			for _, excludedFileSuffix := range excludedFileSuffixes {
				if strings.HasSuffix(resourceDirEntry.Name(), excludedFileSuffix) {
					excludedSuffixPresent = true
					break
				}
			}

			if !resourceDirEntry.IsDir() && includedSuffixPresent && !excludedSuffixPresent {
				resourcePath := filepath.Join(servicePath, resourceDirEntry.Name())
				fileSet := token.NewFileSet()
				resourceFile, err := parser.ParseFile(fileSet, resourcePath, nil, parser.AllErrors)
				if err != nil {
					log.Fatalf("error parsing file: %v", err)
				}

				ast.Inspect(resourceFile, getInspectFunction(fileSet, chunkLineFile))
			}
		}
	}

	cmd := exec.Command("git", "-C", azurermPath, "rev-parse", "HEAD")
	var stdout bytes.Buffer
	cmd.Stdout = &stdout

	err = cmd.Run()
	if err != nil {
		log.Fatalf("error reading Git commit: %v", err)
	}

	if err := os.WriteFile(filepath.Join(dataPath, "azurermCommit.txt"), stdout.Bytes(), 0644); err != nil {
		log.Fatalf("error writing Git commit: %v", err)
	}
}
