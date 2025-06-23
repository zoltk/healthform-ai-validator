# =============================================================================
# modules/networking/locals.tf
# =============================================================================

locals {
  common_tags = merge(
    var.tags,
    {
      Project     = var.project_name
      Environment = var.environment
      Terraform   = "true"
      Component   = "networking"
      CreatedBy   = "terraform"
      Module      = "networking"
    }
  )

  # Calculate subnet CIDRs dynamically
  public_subnet_cidrs   = [for i in range(length(var.availability_zones)) : cidrsubnet(var.vpc_cidr, 8, i + 1)]
  private_subnet_cidrs  = [for i in range(length(var.availability_zones)) : cidrsubnet(var.vpc_cidr, 8, i + 10)]
  database_subnet_cidrs = [for i in range(length(var.availability_zones)) : cidrsubnet(var.vpc_cidr, 8, i + 100)]
}