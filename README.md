## Workernode Group Creation for Multiple-interfaces Attached Instance (e.g. Multus CNI Plugin with EKS/VPC CNI Plugin)
cfn-nodegroup-for-multus-cni 

This is the CloudFormation template for self-managed worker node creation with Multus CNI plugin in EKS. In case of Telecom network function implementation on AWS EKS environment, multus meta-CNI plugin is frequently being requested to make Pod to have multi-homed interfaces(https://github.com/intel/multus-cni). In AWS environment, to use this multus CNI plugin along with VPC CNI plugin, workernode group has to attach multiple interfaces with making those interfaces not to be managed by VPC CNI plugin. This CloudFormation template for self-managed worker node group is to create workernode instances for EKS with having secondary interfaces without being managed by VPC CNI Plugin. As a result of CFN, workernode will spin off with having 1st interface to be VPC CNI controlled default K8s networking and 2nd (3rd, 4th as defined) interface to be for multus interfaces. (If VPC CNI requires more ENIs for assigning Pod IP address, then it attaches more ENIs after multus interfaces in order). 


## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.

## Pre-requisites
- This CFN assumes user already has created VPC, security groups and subnets (even for subnets of multus interfaces). 
- Current Lambda supports maximum 4 additional multus subnets (besides with a default K8s network). But user can modify to increase the number of multus interfaces. 
- **[Important Note]** User must be aware of and responsible of that using this CFN and this mode of multus will cause the number of pods hosted on the workernode to be reduced down because this mode is dedicating certain number of ENIs only for Multus subnet purpose. 
(In general, a number of max Pods on the node has tight dependancy to the number of ENIs available for VPC CNI plugin.)

## Logic in CFN
From the baseline CFN for self-managed node group, below functions are added;
- LifeCycle Hook creation for the self-managed workernode ASG.
- Lambda function creation for multus ENI attachment of 2ndary subnet (using the code (in zip file) pre-uploaded in S3). Current Lambda can support max 4 multus subnets to be attached. While attaching multus interfaces to the instance, also it adds "no_manage" tag to these interfaces so that these would not be controlled by VPC CNI Plugin. 
- CloudWatch Event Rule to trigger Lambda function. 
- Automatic-reboot after the first creation of instance, to kick in life-cycle hook to invoke Lambda for multus interface attachment. 

## Usage 
- Before running this CloudFormation, you have to place lambda_function zip file (lambda_function.py) to your S3 bucket.
- During CFN stack creation,
 -- Select primary private subnet for the parameter of `Subets` where the primary K8s networking interface would be connected to. 
 -- Select 2ndary (Multus) subnet for the parameter of `MultusSubnet1/2/3/4` where multus ENIs will be connected to.
 
## List of CFNs
Based on required number of multus subnets, user can use different CFNs in this GitHub with same Lambda function.
- amazon-eks-nodegroup-multus-1ENI.yaml : 1 multus subnet (1 default k8s network and 1 additional multus network)
- amazon-eks-nodegroup-multus-2ENIs.yaml : 2 multus subnets
- amazon-eks-nodegroup-multus-3ENIs.yaml : 3 multus subnets
- amazon-eks-nodegroup-multus-4ENIs.yaml : 4 multus subnets
