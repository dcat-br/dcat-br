# Validação do DCAT-BR usando SHACL

Para auxiliar na verificação se um catálogo atende ou não às restrições expressas neste Perfil de Aplicação, as restrições nesta especificação são expressas usando SHACL [shacl]. Cada restrição nesta especificação que pôde ser convertida em uma expressão SHACL foi incluída. Assim, esta coleção de expressões SHACL pode ser usada para construir uma verificação de validação para uma troca de dados entre dois sistemas. Um caso de uso típico é a coleta de um catálogo em outro.

Cabe aos implementadores da troca de dados definir a validação que esperam. Cada troca de dados ocorre dentro de um contexto, e esse contexto está além das expressões SHACL aqui apresentadas.

Por exemplo, pode-se saber que os dados trocados não contêm os detalhes das organizações, pois todas são identificadas exclusivamente por um URI deferenciável. Nesse caso, as regras relativas à verificação da existência obrigatória de um nome para cada organização provavelmente não são relevantes. Uma execução estrita das expressões SHACL do DCAT-BR gerará erros, embora os dados estejam disponíveis por meio de um canal diferente. Neste exemplo, é válido não incluir essa verificação nesta etapa de validação.

O exemplo ilustra que, para obter a experiência de usuário adequada em um processo de validação, é preciso considerar o que é efetivamente transferido entre os sistemas e utilizar as restrições que estão dentro do escopo da troca de dados. Para auxiliar nesse processo, as expressões SHACL são agrupadas em arquivos distintos, seguindo as configurações típicas de validação.

## Arquivos SHACL

### shapes.ttl
Restrições relativas à existência, domínio, intervalo literal e cardinalidades.

Este arquivo fornece, para cada classe mencionada no DCAT-BR e que possui propriedades adicionais definidas, um modelo com as restrições correspondentes. As restrições de associação de classe não estão presentes neste arquivo. Estas são compiladas no arquivo `range.ttl`.

### range.ttl
Restrições relativas ao intervalo de objetos.

Este arquivo contém as restrições de intervalo de classe para todas as propriedades no DCAT-BR. Dependendo dos acordos de troca, essas podem ser necessárias para fazer parte do processo de validação. No entanto, elas figuram principalmente no entendimento semântico dos intervalos.

### shapes_recommended.ttl
Restrições relativas à existência de propriedades recomendadas.

Este arquivo contém as restrições sobre propriedades que não são obrigatórias, mas são recomendadas para melhorar a qualidade e interoperabilidade dos metadados. As violações dessas restrições geram avisos (Warning) em vez de erros (Violation).

### imports.ttl
Importa o conhecimento de vocabulário.

Este arquivo fornece as importações que são implicitamente o resultado de reutilizá-las no perfil de aplicação DCAT-BR. As importações apontam para a URL das serializações RDF (principalmente as serializações turtle), pois nem todas as URIs de ontologia têm negociação de conteúdo implementada.

### mdr-vocabularies.shape.ttl
Restrições relativas ao uso de vocabulários controlados.

Este arquivo contém as restrições que validam se os valores usados em propriedades específicas pertencem aos vocabulários controlados do DCAT-BR. Por exemplo, valida se `dct:accrualPeriodicity` usa valores do vocabulário de periodicidade, se `dct:accessRights` usa valores do vocabulário de observância legal, etc.

**Nota:** Algumas URIs de vocabulários ainda não existem e precisam ser criadas. Consulte `CRIAR-VOCABULARIOS.md` para instruções.

### mdr_imports.ttl
Importa as listas de códigos recomendadas.

Este arquivo lista as importações dos vocabulários controlados (SKOS) necessários para validação completa. Inclui vocabulários do DCAT-BR e vocabulários padrão reutilizados.

**Nota:** As URIs dos vocabulários do DCAT-BR precisam ser criadas e publicadas antes de usar este arquivo.

## Uso

Para validar um catálogo, pode ser necessário importar dados adicionais para o validador, como os vocabulários controlados. Estes devem ser obtidos dos locais apropriados.

### Pré-requisito

```bash
pip install pyshacl rdflib
```

### Script recomendado (vários arquivos SHACL)

O DCAT-BR distribui as restrições em vários arquivos (`shapes.ttl`, `range.ttl`, etc.). Use o script na raiz do repositório:

```bash
# a partir da raiz do projeto DCAT-BR
python scripts/validate-shacl.py docs/examples/portal-dataset.ttl

# núcleo obrigatório (shapes.ttl)
python scripts/validate-shacl.py docs/examples/portal-dataset.ttl --suite core

# núcleo + intervalos de classe
python scripts/validate-shacl.py docs/examples/portal-dataset.ttl --suite core+range

# completo (inclui vocabulários MDR)
python scripts/validate-shacl.py docs/examples/portal-dataset.ttl --suite full
```

Suites disponíveis: `core`, `core+range`, `recommended`, `full`.

### PySHACL direto (apenas shapes.ttl)

O PySHACL aceita **um** arquivo de shapes em `-s`. Para validar só o núcleo:

```bash
cd docs/shacl/1.0
python -m pyshacl -s shapes.ttl -f human ../../examples/portal-dataset.ttl
```

**Atenção:** em `python -m pyshacl`, a opção `-i` define **inferência** (`none`, `rdfs`, `owlrl`, `both`), não um arquivo `imports.ttl`. Os arquivos `imports.ttl` e `mdr_imports.ttl` listam `owl:imports` para carregar ontologias em ferramentas que suportam importação de grafos.

### Apache Jena (alternativa)

```bash
shaclvalidate.sh -datafile seu_catalogo.ttl -shapesfile shapes.ttl
```

### Validação Online

Os arquivos SHACL estão configurados para uso com validadores SHACL padrão. Você pode usar:

- [SHACL Playground](https://shacl.org/playground/)
- [TopBraid SHACL Validator](https://www.topquadrant.com/tools/ide-topbraid-composer-maestro-edition/)
- [PySHACL](https://github.com/RDFLib/pySHACL)

## Estrutura dos Arquivos

Cada arquivo SHACL segue a seguinte estrutura:

1. **Prefixos**: Definição de todos os namespaces utilizados
2. **Metadados do arquivo**: Informações sobre o arquivo (formato, conformidade, descrição)
3. **Shapes**: Definições de shapes SHACL para cada classe do DCAT-BR
4. **Propriedades**: Restrições sobre propriedades de cada classe

## Classes Validadas

Os arquivos SHACL validam as seguintes classes do DCAT-BR:

- `dcat:Dataset` - Conjunto de Dados
- `dcat:Distribution` - Distribuição
- `dcat:DataService` - Serviço de Dados
- `dcat:Resource` - Recurso Catalogado
- `foaf:Agent` - Agente (Organização/Pessoa)
- `dct:Location` - Local
- `dct:PeriodOfTime` - Período de Tempo
- `vcard:Organization` - vCard (Ponto de Contato)
- `spdx:Checksum` - Verificação de Integridade

## Propriedades Obrigatórias vs Recomendadas

### Obrigatórias (Violation)
As propriedades obrigatórias geram erros (Violation) quando ausentes ou inválidas:
- `dct:title` - Título
- `dct:description` - Descrição
- `dcat:accessURL` - URL de acesso (para Distribution)
- `dcat:endpointURL` - URL do endpoint (para DataService)

### Recomendadas (Warning)
As propriedades recomendadas geram avisos (Warning) quando ausentes:
- `dcat:contactPoint` - Ponto de contato
- `dcat:distribution` - Distribuições
- `dcat:keyword` - Palavras-chave
- `dcat:theme` - Temas
- `dct:spatial` - Cobertura espacial
- `dct:temporal` - Cobertura temporal

## Referências

- [SHACL Specification](https://www.w3.org/TR/shacl/)
- [DCAT-BR 1.0.0](https://www.gov.br/governodigital/pt-br/infraestrutura-nacional-de-dados/catalogo-nacional-de-dados)
- [DCAT Vocabulary](https://www.w3.org/TR/vocab-dcat-3/)

## Vocabulários Controlados

O DCAT-BR define vocabulários controlados para:

- **Periodicidade** (`dct:accrualPeriodicity`): DIARIA, SEMANAL, MENSAL, etc.
- **Observância Legal** (`dct:accessRights`): Público, Restrito, Sigiloso (vários tipos)
- **Temas** (`dcat:theme`): Economia e Finanças, Saúde, Educação, etc.
- **Tipo de Recurso** (`dct:type`): DADOS, API, DOCUMENTACAO, etc.

**Importante:** As URIs dos vocabulários SKOS ainda precisam ser criadas. Consulte o arquivo `CRIAR-VOCABULARIOS.md` para instruções detalhadas sobre como criar e publicar esses vocabulários.

## Notas de Implementação

- As restrições de vocabulários controlados estão no arquivo `mdr-vocabularies.shape.ttl`.
- Algumas restrições podem não ser expressáveis em SHACL puro e podem requerer validação adicional em código.
- Os validadores SHACL podem ter diferentes níveis de suporte para recursos avançados do SHACL.
- Antes de usar `mdr_imports.ttl`, certifique-se de que os vocabulários SKOS foram criados e publicados nas URIs especificadas.

