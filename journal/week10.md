# Week 10 — CloudFormation Part 1

- install cfn lint
`pip install cfn-lint` 

add to .gitpod.yml

```yml
  - name: cfn
    before: |
      pip install cfn-link
```

 - install cgn-guard and add the below to .gitpod

 `cargo install cfn-guard`


## CFN For Networking Layer

- create an s3 bucket to contain artificats for CloudFormation.
I created a bucked called `cfn-mycruddur-artifacts`

```sh
aws s3 mk s3://cfn-mycruddur-artifacts
export CFN_BUCKET="cfn-mycruddur-artifacts"
gp env CFN_BUCKET="cfn-mycruddur-artifacts"
```


- install cfn-toml

```sh
gem install cfn-toml`
```
also add it to the _CFN_ section of our `.gitpod.yml` file.

